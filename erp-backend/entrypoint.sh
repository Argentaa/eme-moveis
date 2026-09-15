#!/bin/sh
# Entrypoint erp-backend: aplica migracoes (alembic), garante admin inicial,
# depois sobe o gunicorn.
# Idempotente: migracoes 0001-0004 sao guardadas (inspector / IF NOT EXISTS);
# seed_admin.py faz upsert (nunca duplica, nunca quebra o boot).
set -e
python -m alembic upgrade head
python seed_admin.py || echo "AVISO: seed_admin falhou (verifique ADMIN_* e DATABASE_URL)"
exec gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app