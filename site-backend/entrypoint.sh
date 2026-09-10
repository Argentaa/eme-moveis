#!/bin/sh
# Entrypoint site-backend: inicializa schema + seed UMA vez antes do gunicorn.
# Evita corrida de create_all() entre workers no primeiro boot em banco vazio.
set -e
python -c "from app import create_app; create_app(); print('site init ok')" || echo "AVISO: site init falhou (verifique DATABASE_URL)"
exec gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 60 wsgi:app
