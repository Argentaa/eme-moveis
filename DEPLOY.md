# EME Móveis — Deploy no Dokploy (app tipo Compose)

Stack: `db` (Postgres 16) + `erp-backend` (Flask :5000) + `erp-frontend`
(nginx :80 → ERP) + `site-backend` (Flask :5001) + `site-frontend`
(nginx :80 → site). Backends só na rede interna; publique os **2 frontends**.

## 0. Segurança (faça ANTES do primeiro deploy)

O zip original veio com `.env` preenchidos
(`eme-moveis/eme-moveis/.../gerenciamento-eme/.env` e `eme_backend/.env`).
**Considere esses segredos vazados**: gere tudo novo e NÃO commite `.env`.

```bash
python3 -c "import secrets; print(secrets.token_hex(64))"  # rode 2x: ERP + SITE
rm /workspace/eme-moveis/eme-moveis/eme-moveis/gerenciamento-eme/.env \
   /workspace/eme-moveis/eme-moveis/eme-moveis/gerenciamento-eme/eme_backend/.env
```

Suba para git só a raiz nova (`docker-compose.yml`, `erp-backend/`,
`site-backend/`, `erp-frontend/`, `site-frontend/`, `backup.sh`, docs).
O `backup_emebd_final.sql` (com dados reais de clientes) fica **fora do
repo** por LGPD — não commite; leve o arquivo por outro caminho (seção 4).

## 1. Variáveis no painel (Environment)

| Variável | Valor |
|---|---|
| `POSTGRES_PASSWORD` | senha forte do banco |
| `ERP_SECRET_KEY` | 128 hex (comando acima) |
| `ERP_ADMIN_PASSWORD` | senha do admin do ERP |
| `SITE_JWT_SECRET` | outro 128 hex, diferente do ERP |
| `SITE_ADMIN_PASS` | senha do admin do site |
| `ERP_JWT_MINUTES` | `720` (opcional) |
| `ERP_CORS_ORIGINS` | `*` ou o domínio do ERP (opcional) |
| `ERP_ADMIN_USER/NAME/EMAIL`, `SITE_ADMIN_USER` | defaults ok (opcional) |

## 2. Domínios (Dokploy → Domains)

- ERP: aponte um domínio para `erp-frontend:80`
- Site: aponte outro domínio para `site-frontend:80`

Nada de porta publicada: o compose usa `expose`, o proxy do Dokploy resolve.

## 3. Deploy + checagem

1. Deploy pelo painel. Aguarde os 5 containers `healthy`.
2. No navegador: `https://SEU-DOMINIO-ERP/api/health` →
   `{"app":"eme-moveis-erp","ok":true`.
3. Site: `https://SEU-DOMINIO-SITE/api/health` →
   `{"status":"ok","database":"up"}`.

## 4. Migrar os dados reais (uma vez)

O banco sobe vazio (só admin + funil padrão). O dump **não vai no repo**;
copie o arquivo por fora (SCP, upload no Dokploy, etc.) para dentro do
container e importe:

```bash
ERP=$(docker ps --format '{{.Names}}' | grep erp-backend | head -n1)
docker cp /caminho/local/backup_emebd_final.sql "$ERP:/tmp/backup_emebd_final.sql"
docker exec "$ERP" python migrate_mysql_dump.py /tmp/backup_emebd_final.sql
# esperado: OK: 190 registros migrados.
docker exec "$ERP" python seed_admin.py
# esperado: admin atualizado: admin   (redefine a senha para ERP_ADMIN_PASSWORD)
```

Ordem importa: **migrate primeiro, seed depois** (o migrate preserva os ids
originais; o seed faz upsert por username e deixa sua senha valendo).
O script é idempotente: re-rodar importa `+0` (seguro repetir).

Conferência (números do dump): 18 clientes, 4 projetos, 87 lançamentos,
24 itens de estoque, 14 eventos de agenda, 6 colunas CRM + 5 de projetos,
DRE/CRM respondendo. Faça login no ERP e confira Dashboard e Relatórios.

Site: login em `/admin` com `SITE_ADMIN_USER/SITE_ADMIN_PASS`. O conteúdo
exemplo (6 projetos, timeline) já vem seedado; edite pelo painel.

## 5. Backup (cron no host do Dokploy)

```bash
POSTGRES_USER=eme POSTGRES_DB=eme ./backup.sh /var/backups/eme-moveis
# cron diário 3h: 0 3 * * * cd /caminho/do/repo && POSTGRES_USER=eme POSTGRES_DB=eme ./backup.sh
```

Gera `eme-<data>.sql.gz` + `uploads-<data>.tar.gz`, retenção de 14 dias.
**Teste o restore** num banco à parte antes de confiar.

## Notas

- Todo restart do `erp-backend` roda `seed_admin.py`: a senha do admin volta
  a ser `ERP_ADMIN_PASSWORD` (comportamento intencional).
- As colunas do funil do dump são preservadas (não sobrescritas pelos defaults).
- Uploads do site vivem no volume `site_uploads` — sem ele, re-deploy perde imagens.
- Chave JWT curta (<32 bytes) funciona mas gera warning: use sempre 128 hex.
