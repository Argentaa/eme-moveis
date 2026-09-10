#!/bin/sh
# Entrypoint erp-backend: garante schema + admin inicial, depois sobe o gunicorn.
# Idempotente: seed_admin.py faz upsert (nunca duplica, nunca quebra o boot).
set -e
python seed_admin.py || echo "AVISO: seed_admin falhou (verifique ADMIN_* e DATABASE_URL)"
exec gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app
