#!/usr/bin/env bash
set -e

# Charger .env si présent (utile lors d'un docker run sans compose)
#!/usr/bin/env bash
set -e

# Charger .env si présent
[ -f "/app/.env" ] && export $(grep -v '^#' /app/.env | xargs)

DB_ENGINE=${DB_ENGINE:-sqlite}

if [ "$DB_ENGINE" = "postgres" ]; then
  echo "⏳ Attente de PostgreSQL (${DB_HOST}:${DB_PORT}) ..."
  python - <<'PYCODE'
import os, time, sys
import psycopg
host = os.getenv("DB_HOST","db"); port=int(os.getenv("DB_PORT","5432"))
dbname=os.getenv("DB_NAME","postgres"); user=os.getenv("DB_USER","postgres")
password=os.getenv("DB_PASSWORD","")
for i in range(60):
    try:
        with psycopg.connect(host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=3):
            print("✅ Base accessible."); sys.exit(0)
    except Exception: time.sleep(1)
print("❌ Impossible de joindre la base."); sys.exit(1)
PYCODE
else
  echo "🗃️ Mode SQLite — pas d'attente de BDD distante."
fi

# (le reste de l'entrypoint inchangé : startproject, migrate, collectstatic, etc.)


# Créer le projet Django au premier démarrage si absent
if [ ! -f "/app/manage.py" ]; then
  echo "📦 Création du squelette Django (config)..."
  django-admin startproject config .
fi

echo "🔧 Migrations"
python manage.py migrate --noinput

# Collecte des statics (optionnel en dev)
python manage.py collectstatic --noinput || true

# Superuser auto si variables définies (optionnel)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "👤 Création/maj du superuser"
  python manage.py shell <<PY
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(username="${DJANGO_SUPERUSER_USERNAME}", defaults={"email":"${DJANGO_SUPERUSER_EMAIL}"})
if created:
    u.set_password("${DJANGO_SUPERUSER_PASSWORD}")
    u.is_superuser = True
    u.is_staff = True
    u.save()
PY
fi

# Choix runserver (dev) vs gunicorn (prod)
if [ "${DEBUG}" = "1" ]; then
  echo "🚀 Démarrage serveur dev"
  exec python manage.py runserver 0.0.0.0:80
else
  echo "🚀 Démarrage gunicorn (prod)"
  exec gunicorn config.wsgi:application --bind 0.0.0.0:80 --workers 3
fi
