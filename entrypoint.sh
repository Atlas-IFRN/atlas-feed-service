#!/bin/bash
set -e

# Garante que o schema deste serviço exista ANTES de migrar.
# O postgres/init.sql só roda em volume novo; em bancos já existentes ele é
# ignorado, então cada serviço cria (idempotentemente) o próprio schema aqui.
# CREATE SCHEMA IF NOT EXISTS funciona mesmo com o search_path apontando para
# um schema ainda inexistente (PGOPTIONS=-c search_path=feed,public).
echo "==> Ensuring database schema exists..."
python <<'PY'
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE SCHEMA IF NOT EXISTS feed")
print("    schema 'feed' pronto.")
PY

echo "==> Running database migrations..."
python manage.py migrate --noinput

# --nostatic desativa o StaticFilesHandler do runserver. Sem isso, com
# DEBUG=True o Django recusa iniciar ("runserver can't serve media if MEDIA_URL
# is within STATIC_URL"), pois as imagens dos posts ficam sob /api/feed/static/.
# Os uploads seguem servidos pela rota de MEDIA em config/urls.py.
echo "==> Starting Django dev server on :8000..."
exec python manage.py runserver 0.0.0.0:8000 --nostatic
