# Image légère Python
FROM python:3.12-slim

# Installer dépendances système utiles
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Empêcher le buffering Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dossier de travail
WORKDIR /app

# Dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint & code
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Pour le dev, on montera le volume ./web:/app
EXPOSE 8000
