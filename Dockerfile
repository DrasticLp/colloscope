# Image Python légère
FROM python:3.11-slim

# Désactive le buffering Python (logs immédiats)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dossier de travail
WORKDIR /app

# Dépendances système minimales (facultatif)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Installe les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le script
COPY main.py .

# Par défaut, écrit le CSV dans /out (volume conseillé)
ENV OUT_DIR=/out

# Commande par défaut
CMD ["python", "main.py"]
