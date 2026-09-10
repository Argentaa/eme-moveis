# EME Móveis — ERP + Site (Flask + Postgres)

Migração completa da stack antiga (FastAPI+MySQL e Node+MySQL) para
**Flask + Postgres**, pronta para deploy no Dokploy via `docker-compose.yml`.

```
eme-moveis/
├── docker-compose.yml   # db + erp-backend + erp-frontend + site-backend + site-frontend
├── DEPLOY.md            # passo a passo do deploy (leia antes de subir)
├── .env.example         # modelo de variáveis (nunca commite o .env real)
├── backup.sh            # backup PG + uploads (cron)
├── erp-backend/         # Flask factory, 8 blueprints, Alembic, pytest (11 testes)
│   ├── migrate_mysql_dump.py        # MySQL dump → Postgres (idempotente; dump fora do repo, ver DEPLOY.md §4)
│   └── seed_admin.py                # upsert do admin via ADMIN_* (roda no boot)
├── site-backend/        # Flask do site institucional, pytest (7 testes)
├── erp-frontend/        # React ERP (build nginx, proxy /api → erp-backend)
├── site-frontend/       # React do site (build nginx, proxy /api+/uploads)
└── eme-moveis/          # zip ORIGINAL intacto (referência; .env de lá = vazado, gerar novos)
```

Contrato REST preservado: os frontends React não foram alterados em lógica
(só Dockerfile/nginx). Detalhes de deploy, migração e backup: **DEPLOY.md**.
