#!/usr/bin/env bash
# Backup do Postgres (db) + uploads do site. Rode no host do Dokploy via cron.
# Uso: ./backup.sh [/caminho/para/backups]
set -euo pipefail
DEST="${1:-/var/backups/eme-moveis}"
mkdir -p "$DEST"
STAMP="$(date +%Y%m%d-%H%M%S)"
PROJECT="$(docker ps --format '{{.Names}}' | grep -m1 -oE '^[a-z0-9_-]*eme[a-z0-9_-]*' || true)"
DB_CT="$(docker ps --format '{{.Names}}' | grep -E 'db|postgres' | head -n1)"
if [ -z "$DB_CT" ]; then
  echo "ERRO: container do postgres não encontrado (docker ps)." >&2
  exit 1
fi
docker exec "$DB_CT" pg_dump -U "${POSTGRES_USER:-eme}" "${POSTGRES_DB:-eme}" | gzip > "$DEST/eme-$STAMP.sql.gz"
SITE_CT="$(docker ps --format '{{.Names}}' | grep -E 'site-backend' | head -n1)"
if [ -n "$SITE_CT" ]; then
  docker cp "$SITE_CT:/app/uploads" "$DEST/uploads-$STAMP" >/dev/null 2>&1 || true
  tar -czf "$DEST/uploads-$STAMP.tar.gz" -C "$DEST" "uploads-$STAMP" && rm -rf "$DEST/uploads-$STAMP"
fi
# Retenção: 14 dias
find "$DEST" -name 'eme-*.sql.gz' -mtime +14 -delete
find "$DEST" -name 'uploads-*.tar.gz' -mtime +14 -delete
echo "Backup OK: $DEST/eme-$STAMP.sql.gz"
