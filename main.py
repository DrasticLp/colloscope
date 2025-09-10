"""
Planificateur de colles (22 semaines, 16 groupes) – OR-Tools CP-SAT
Contraintes **souples** (on minimise les violations) pour éviter l'infaisabilité.

Inclusions demandées :
- Ajout **Mme Cointault** (Physique Mer 16–17 et 17–18) – distinct de **Mr Cointault** (Mer 15–16).
- Ajout **Mr Huart** (Physique Jeu 17–18).
- Remplacements S2I : S6 & S12 → **Brodelle** remplace **Roux** et prend aussi **Mer 18–19** ces semaines.
- Remplacement Physique S12 : **Zénag** remplace **Berteloot** (Mer 14–15, 15–16, 18–19) et Berteloot indispo S12.

Contraintes dures (obligatoires) :
- Chaque **semaine/groupe**: exactement **1** colle dans {Maths, Anglais} **et** exactement **1** colle dans {Physique, S2I}.
- Capacité : **au plus 1 groupe** par créneau.
- Pas de **chevauchement horaire** pour un même groupe (même jour).
- Interdits Groupe 3 : pas (Anglais, **Mme Lachot**) ; pas (Physique, **Mr Pauchet**).

Contraintes souples (pénalisées, donc évitées au maximum) :
- Maths **= 11 semaines** par groupe (avec pénalité |#Maths−11|).
- Maths **non consécutives** (pénalité par paire de semaines consécutives).
- **G1 & G2** : éviter Maths la même semaine (pénalité si simultané).
- Ratio **S2I/Physique** par **fenêtre glissante de 4 semaines** : viser **exactement 1 S2I** (→ 3 Phys) par groupe (pénalité |#S2I−1| par fenêtre).
- **Éviter 2 colles le même jour** (pénalité) et **éviter 2 colles consécutives** le même jour (pénalité supplémentaire).
- **Éviter même prof 2 semaines d'affilée** pour un groupe (toutes matières confondues) (pénalité).
- Couverture ≥1 occurrence **Mme Goubet** et **Mr Berteloot** par **bloc de 8 semaines** (S12 ignorée pour Berteloot) — pénalité si manqué.
- Couverture “**autres profs**” ≥1 fois sur S1..S16 pour chaque groupe (pénalité faible).

Sortie : CSV `colles_or_tools.csv` trié par Matière → Jour → Prof → Semaine.

Dépendance : `pip install ortools`
"""
import time

from ortools.sat.python import cp_model
from collections import defaultdict, OrderedDict
import csv

class MyCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0
        self.__t0 = time.time()

    def OnSolutionCallback(self):
        self.__solution_count += 1
        elapsed = time.time() - self.__t0
        print(f"[{elapsed:6.2f}s/21600s] Solution #{self.__solution_count} "
              f"Objective = {self.ObjectiveValue():.0f} "
              f"(Branches={self.NumBranches()}, Conflicts={self.NumConflicts()})")

    def SolutionCount(self):
        return self.__solution_count
solution_printer = MyCallback([])


# =====================
# Paramètres
# =====================
WEEKS = list(range(1, 23))
GROUPS = list(range(1, 17))  # 16 groupes
ALL_W = set(WEEKS)
DAY_ORDER = {"Lundi": 1, "Mardi": 2, "Mercredi": 3, "Jeudi": 4, "Vendredi": 5, "Samedi": 6, "Dimanche": 7}
BLOCKS_8 = [set(range(1, 9)), set(range(9, 17)), set(range(17, 23))]

# Poids des pénalités (ajuster si besoin)
W_MATH_COUNT = 15
W_MATH_CONSEC = 20
W_M12_SIMULT = 25
W_S2I_WINDOW = 25
W_SAME_DAY = 6
W_CONSEC_IN_DAY = 10
W_SAME_TEACHER_CONSEC = 8
W_COVER_GOUBET = 20
W_COVER_BERTELOOT = 20
W_COVER_OTHERS = 2

# =====================
# Données des créneaux
# =====================
teachers = []

# ------- Maths -------
teachers += [
    ("Maths", "Mme Goubet", [("Mardi", "16:00", "17:00", ALL_W), ("Mardi", "17:00", "18:00", ALL_W)]),
    ("Maths", "Mr Pruvost", [("Jeudi", "17:00", "18:00", ALL_W)]),
    ("Maths", "Mme Coquet", [("Mardi", "16:45", "17:45", ALL_W)]),
    ("Maths", "Mr Jourdan", [("Mercredi", "16:00", "17:00", ALL_W), ("Mercredi", "17:00", "18:00", ALL_W)]),
    ("Maths", "Mr Gammelin", [("Mercredi", "15:00", "16:00", ALL_W)]),
    ("Maths", "Mme Séverin", [("Mercredi", "16:00", "17:00", ALL_W)]),
]

# ------- S2I ---------
W_NO_ROUX = ALL_W - {6, 12}
teachers += [
    ("S2I", "Mr Roux", [("Mercredi", "18:00", "19:00", W_NO_ROUX)]),
    ("S2I", "Mr Brodelle", [
        ("Mercredi", "15:00", "16:00", ALL_W),
        ("Mercredi", "16:00", "17:00", ALL_W),
        ("Jeudi", "17:00", "18:00", ALL_W),
        # Remplacement de Roux sur Mer 18–19 aux semaines 6 et 12
        ("Mercredi", "18:00", "19:00", {6, 12}),
    ]),
]

# ------ Anglais -------
teachers += [
    ("Anglais", "Mr Devin", [
        ("Mardi", "16:00", "17:00", ALL_W),
        ("Mardi", "17:00", "18:00", ALL_W),
        ("Mercredi", "14:00", "15:00", ALL_W),
        ("Mercredi", "16:00", "17:00", ALL_W),
    ]),
    ("Anglais", "Mme Lachot", [("Lundi", "17:00", "18:00", ALL_W), ("Lundi", "18:00", "19:00", ALL_W)]),
    ("Anglais", "Mr Tallu", [("Mardi", "16:00", "17:00", ALL_W)]),
    ("Anglais", "Mr Capes", [("Jeudi", "17:00", "18:00", ALL_W)]),
]

# ------ Physique ------
BERT_W_18_19 = {1, 10, 11, 17, 18, 19, 20, 21, 22}
BERT_W_14_15 = {2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16}
W_NO_BERTELOOT = ALL_W - {12}

teachers += [
    ("Physique", "Mr Pauchet", [("Lundi", "18:00", "19:00", ALL_W)]),
    ("Physique", "Mr Cousin", [("Mardi", "16:00", "17:00", ALL_W)]),
    ("Physique", "Mr Brunier", [("Mardi", "16:00", "17:00", ALL_W)]),
    ("Physique", "Mr Zénag", [("Mardi", "17:00", "18:00", ALL_W), ("Mardi", "18:00", "19:00", ALL_W)]),
    ("Physique", "Mr Berteloot", [
        ("Mercredi", "15:00", "16:00", W_NO_BERTELOOT),
        ("Mercredi", "18:00", "19:00", BERT_W_18_19 - {12}),
        ("Mercredi", "14:00", "15:00", BERT_W_14_15 - {12}),
    ]),
    ("Physique", "Mr Cointault", [("Mercredi", "15:00", "16:00", ALL_W)]),
    ("Physique", "Mr Labasque", [("Mercredi", "16:00", "17:00", ALL_W)]),
    # Ajouts demandés
    ("Physique", "Mme Cointault", [("Mercredi", "16:00", "17:00", ALL_W), ("Mercredi", "17:00", "18:00", ALL_W)]),
    ("Physique", "Mr Huart", [("Jeudi", "17:00", "18:00", ALL_W)]),
]

# Remplacement S12 (Berteloot → Zénag sur Mer 14–15, 15–16, 18–19)
REPLACE_W12 = [
    ("Physique", "Mr Zénag", ("Mercredi", "14:00", "15:00", {12})),
    ("Physique", "Mr Zénag", ("Mercredi", "15:00", "16:00", {12})),
    ("Physique", "Mr Zénag", ("Mercredi", "18:00", "19:00", {12})),
]
for subj, teach, tup in REPLACE_W12:
    day, start, end, weeks = tup
    teachers.append((subj, teach, [(day, start, end, weeks)]))

# ----------------------
# Construction des slots
# ----------------------
slots = []
for subj, teach, times in teachers:
    for (day, start, end, weeks) in times:
        weeks_set = ALL_W if weeks is ALL_W else set(weeks)
        for w in WEEKS:
            if w in weeks_set:
                slots.append({
                    "subject": subj,
                    "teacher": teach,
                    "week": w,
                    "day": day,
                    "start": start,
                    "end": end,
                })
for i, s in enumerate(slots):
    s["id"] = i

# Index
slots_by_week = defaultdict(list)
slots_by_week_subject = defaultdict(list)
slots_by_week_teacher = defaultdict(list)
slots_by_w_day = defaultdict(list)  # (w, day) → slots de ce jour
for s in slots:
    w = s["week"]
    slots_by_week[w].append(s)
    slots_by_week_subject[(w, s["subject"])].append(s)
    slots_by_week_teacher[(w, s["teacher"])].append(s)
    slots_by_w_day[(w, s["day"])].append(s)


# Utilitaires temps
def to_min(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def overlap(s1, s2) -> bool:
    if s1["day"] != s2["day"]:
        return False
    a1, a2 = to_min(s1["start"]), to_min(s1["end"])
    b1, b2 = to_min(s2["start"]), to_min(s2["end"])
    return not (a2 <= b1 or b2 <= a1)


def consecutive(s1, s2) -> bool:
    return s1["day"] == s2["day"] and (s1["end"] == s2["start"] or s2["end"] == s1["start"])


# =====================
# Modèle CP-SAT
# =====================
model = cp_model.CpModel()
X = {}
for s in slots:
    w, sid = s["week"], s["id"]
    for g in GROUPS:
        X[(w, g, sid)] = model.NewBoolVar(f"x_w{w}_g{g}_s{sid}")

# Capacité slot (au plus 1 groupe)
for s in slots:
    w, sid = s["week"], s["id"]
    model.Add(sum(X[(w, g, sid)] for g in GROUPS) <= 1)

# 2 colles / semaine / groupe : 1 MA (Maths/Anglais) et 1 PS (Physique/S2I)
for w in WEEKS:
    MA = [s for s in slots_by_week[w] if s["subject"] in ("Maths", "Anglais")]
    PS = [s for s in slots_by_week[w] if s["subject"] in ("Physique", "S2I")]
    for g in GROUPS:
        model.Add(sum(X[(w, g, s["id"])] for s in MA) == 1)
        model.Add(sum(X[(w, g, s["id"])] for s in PS) == 1)

# Pas de chevauchement horaire (même jour) pour un groupe
for w in WEEKS:
    for day, Sday in slots_by_w_day.items():
        pass  # placeholder
# Correction: itère correctement par (w, day)
for (w, day), Sday in slots_by_w_day.items():
    for g in GROUPS:
        for i in range(len(Sday)):
            for j in range(i + 1, len(Sday)):
                s1, s2 = Sday[i], Sday[j]
                if overlap(s1, s2):
                    model.Add(X[(w, g, s1["id"])] + X[(w, g, s2["id"])] <= 1)

# Interdits Groupe 3
for w in WEEKS:
    for s in slots_by_week[w]:
        if s["subject"] == "Anglais" and s["teacher"] == "Mme Lachot":
            model.Add(X[(w, 3, s["id"])] == 0)
        if s["subject"] == "Physique" and s["teacher"] == "Mr Pauchet":
            model.Add(X[(w, 3, s["id"])] == 0)

# =====================
# Variables auxiliaires pour pénalités
# =====================
# Maths par semaine (bool)
M = {}  # M[(w,g)] = 1 si Maths pour g la semaine w
for w in WEEKS:
    for g in GROUPS:
        m_sum = sum(X[(w, g, s["id"])] for s in slots_by_week_subject[(w, "Maths")])
        M[(w, g)] = model.NewBoolVar(f"is_math_w{w}_g{g}")
        # Comme m_sum ∈ {0,1}, on peut forcer l'égalité
        model.Add(m_sum == M[(w, g)])

# Prof utilisé par semaine (bool)
B = {}  # B[(t,w,g)] = 1 si prof t voit le groupe g en semaine w
all_teachers = sorted({s["teacher"] for s in slots})
for t in all_teachers:
    for w in WEEKS:
        for g in GROUPS:
            sum_twg = sum(X[(w, g, s["id"])] for s in slots_by_week_teacher[(w, t)])
            b = model.NewBoolVar(f"use_{t}_w{w}_g{g}")
            # 0 ≤ sum ≤ 2 ; forcer b = 1 si sum≥1
            model.Add(sum_twg >= b)
            model.Add(sum_twg <= 2 * b)
            B[(t, w, g)] = b


# Comptage S2I par fenêtre de 4 semaines
def s2i_count_window(g, w0):
    return sum(X[(w, g, s["id"])] for w in range(w0, w0 + 4) for s in slots_by_week_subject[(w, "S2I")])


# =====================
# Pénalités (variables + objectif)
# =====================
penalties = []

# 1) Maths = 11 semaines (|count-11|)
for g in GROUPS:
    count_math = sum(M[(w, g)] for w in WEEKS)
    diff = model.NewIntVar(0, 22, f"diff_math_g{g}")
    model.Add(diff >= count_math - 11)
    model.Add(diff >= 11 - count_math)
    penalties.append(W_MATH_COUNT * diff)

# 2) Maths non consécutives (pénalité par paire consécutive)
for g in GROUPS:
    for w in WEEKS[:-1]:
        z = model.NewBoolVar(f"math_consec_w{w}_g{g}")
        model.Add(z <= M[(w, g)])
        model.Add(z <= M[(w + 1, g)])
        model.Add(z >= M[(w, g)] + M[(w + 1, g)] - 1)
        penalties.append(W_MATH_CONSEC * z)

# 3) G1 & G2 : éviter Maths la même semaine
for w in WEEKS:
    z = model.NewBoolVar(f"math_12_same_w{w}")
    model.Add(z <= M[(w, 1)])
    model.Add(z <= M[(w, 2)])
    model.Add(z >= M[(w, 1)] + M[(w, 2)] - 1)
    penalties.append(W_M12_SIMULT * z)

# 4) S2I/Physique (fenêtre 4 semaines) : viser S2I=1 (|#S2I-1|)
for g in GROUPS:
    for w0 in range(1, 22 - 4 + 2):  # 1..19
        s2i_4 = s2i_count_window(g, w0)
        diff = model.NewIntVar(0, 4, f"diff_s2i_w{w0}_g{g}")
        model.Add(diff >= s2i_4 - 1)
        model.Add(diff >= 1 - s2i_4)
        penalties.append(W_S2I_WINDOW * diff)

# 5) Éviter 2 colles le même jour (et consécutives)
for w in WEEKS:
    for g in GROUPS:
        # a) même jour (exactement 2 colles sur un même jour)
        y_day_twos = []
        for day in DAY_ORDER.keys():
            Sday = slots_by_w_day.get((w, day), [])
            if not Sday:
                continue
            cnt = sum(X[(w, g, s["id"])] for s in Sday)
            y = model.NewBoolVar(f"same_day_w{w}_g{g}_{day}")
            # y=1 ⇒ cnt≥2 ; y=0 ⇒ cnt≤1
            model.Add(cnt >= 2).OnlyEnforceIf(y)
            model.Add(cnt <= 1).OnlyEnforceIf(y.Not())
            y_day_twos.append(y)
        if y_day_twos:
            penalties.append(W_SAME_DAY * sum(y_day_twos))

        # b) consécutives dans la journée (back-to-back)
        for day in DAY_ORDER.keys():
            Sday = slots_by_w_day.get((w, day), [])
            for i in range(len(Sday)):
                for j in range(i + 1, len(Sday)):
                    s1, s2 = Sday[i], Sday[j]
                    if consecutive(s1, s2):
                        zc = model.NewBoolVar(f"consec_w{w}_g{g}_{s1['id']}_{s2['id']}")
                        model.Add(zc <= X[(w, g, s1["id"])])
                        model.Add(zc <= X[(w, g, s2["id"])])
                        model.Add(zc >= X[(w, g, s1["id"])] + X[(w, g, s2["id"])] - 1)
                        penalties.append(W_CONSEC_IN_DAY * zc)

# 6) Pas le même prof 2 semaines d'affilée (pénalité)
for t in all_teachers:
    for g in GROUPS:
        for w in WEEKS[:-1]:
            z = model.NewBoolVar(f"same_prof_consec_{t}_g{g}_w{w}")
            model.Add(z <= B[(t, w, g)])
            model.Add(z <= B[(t, w + 1, g)])
            model.Add(z >= B[(t, w, g)] + B[(t, w + 1, g)] - 1)
            penalties.append(W_SAME_TEACHER_CONSEC * z)

# 7) Couverture Goubet/Berteloot par blocs de 8 semaines (pénalisée si manquée)
for g in GROUPS:
    for block in BLOCKS_8:
        # Goubet
        sum_g = sum(X[(w, g, s["id"])] for w in block for s in slots_by_week_teacher[(w, "Mme Goubet")])
        miss_g = model.NewBoolVar(f"miss_goubet_blk{min(block)}_{max(block)}_g{g}")
        model.Add(sum_g >= 1).OnlyEnforceIf(miss_g.Not())
        model.Add(sum_g <= 0).OnlyEnforceIf(miss_g)
        penalties.append(W_COVER_GOUBET * miss_g)
        # Berteloot (ignorer S12)
        blk_wo12 = [w for w in block if w != 12]
        if blk_wo12:
            sum_b = sum(X[(w, g, s["id"])] for w in blk_wo12 for s in slots_by_week_teacher[(w, "Mr Berteloot")])
            miss_b = model.NewBoolVar(f"miss_berteloot_blk{min(block)}_{max(block)}_g{g}")
            model.Add(sum_b >= 1).OnlyEnforceIf(miss_b.Not())
            model.Add(sum_b <= 0).OnlyEnforceIf(miss_b)
            penalties.append(W_COVER_BERTELOOT * miss_b)

# 8) Couverture autres profs en S1..S16 (pénalité faible si jamais vus)
for t in all_teachers:
    if t in ("Mme Goubet", "Mr Berteloot"):
        continue
    for g in GROUPS:
        sum_t = sum(X[(w, g, s["id"])] for w in range(1, 17) for s in slots_by_week_teacher[(w, t)])
        miss = model.NewBoolVar(f"miss_other_{t}_g{g}")
        model.Add(sum_t >= 1).OnlyEnforceIf(miss.Not())
        model.Add(sum_t <= 0).OnlyEnforceIf(miss)
        penalties.append(W_COVER_OTHERS * miss)

# ---------------------
# Objectif : minimiser la somme pondérée des pénalités
# ---------------------
model.Minimize(sum(penalties))

# =====================
# Résolution
# =====================
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 21600.0
solver.parameters.num_search_workers = 12
status = solver.SolveWithSolutionCallback(model, solution_printer)

if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("Pas de solution trouvée (délai). Vous pouvez augmenter max_time_in_seconds ou assouplir les poids.")
else:
    # Agrégation par créneau (groupes affectés)
    rows = []
    for w in WEEKS:
        alloc = defaultdict(list)
        for s in sorted(slots_by_week[w],
                        key=lambda s: (DAY_ORDER.get(s['day'], 99), s['start'], s['end'], s['subject'], s['teacher'])):
            sid = s["id"]
            for g in GROUPS:
                if solver.Value(X[(w, g, sid)]) == 1:
                    key = (s["subject"], s["day"], s["teacher"], s["start"], s["end"], w)
                    alloc[key].append(g)
        for key, glist in alloc.items():
            subj, day, teach, start, end, w = key
            groups_str = ", ".join(map(str, sorted(glist)))
            rows.append({
                "Subject": subj, "Day": day, "Teacher": teach, "Start": start, "End": end,
                "Week": w, "Groups": groups_str
            })

    # Tri et export CSV
    rows_sorted = sorted(rows, key=lambda r: (
        r["Subject"],
        DAY_ORDER.get(r["Day"], 99),
        r["Teacher"],
        r["Week"],
        r["Start"],
        r["End"]
    ))
    csv_path = "colles_or_tools.csv"
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Subject", "Day", "Teacher", "Start", "End", "Week", "Groups"])
        writer.writeheader()
        writer.writerows(rows_sorted)
    print(f"CSV généré : {csv_path}")

    # Petit récap des principales pénalités (diagnostic)
    obj = solver.ObjectiveValue()
    print(f"Objectif (somme pondérée des pénalités) = {obj:.0f}")
