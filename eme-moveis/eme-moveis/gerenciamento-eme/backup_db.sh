#!/bin/bash
# ============================================================
# backup_db.sh — backup diário do banco MySQL do EME Móveis
#
# Como usar:
#   1. Coloque este arquivo em /opt/eme-moveis/backup_db.sh (ou outro local)
#   2. chmod +x backup_db.sh
#   3. Configure no crontab (veja instruções no final deste arquivo)
#
# Os backups ficam em BACKUP_DIR, comprimidos, com data no nome.
# Backups com mais de RETENTION_DAYS dias são apagados automaticamente.
# ============================================================

set -euo pipefail

# Ajuste estes caminhos para o seu ambiente
PROJECT_DIR="/opt/eme-moveis"
BACKUP_DIR="/opt/eme-moveis/backups"
RETENTION_DAYS=14

# Carrega as variáveis do .env do projeto (para pegar usuário/senha do banco)
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "ERRO: arquivo .env não encontrado em $PROJECT_DIR"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/emebd_${TIMESTAMP}.sql.gz"

echo "[$(date)] Iniciando backup do banco emebd..."

cd "$PROJECT_DIR"
docker compose exec -T mysql mysqldump \
    -u root -p"${MYSQL_ROOT_PASSWORD}" \
    --single-transaction \
    --quick \
    --lock-tables=false \
    "${DB_NAME:-emebd}" | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup salvo em: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Remove backups mais antigos que RETENTION_DAYS
find "$BACKUP_DIR" -name "emebd_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "[$(date)] Backup concluído. Backups com mais de ${RETENTION_DAYS} dias foram removidos."

# ============================================================
# Para agendar este script diariamente às 2h da manhã, rode:
#   crontab -e
# E adicione a linha (ajustando o caminho se necessário):
#   0 2 * * * /opt/eme-moveis/backup_db.sh >> /opt/eme-moveis/backups/backup.log 2>&1
#
# IMPORTANTE: estes backups ficam na MESMA máquina física. Para proteção
# real contra falha de disco/incêndio/roubo, copie-os periodicamente para
# fora da VM (outro servidor, um serviço de armazenamento em nuvem, ou um
# pendrive/HD externo guardado em outro local). Um backup que vive só no
# mesmo disco que ele protege não é uma proteção completa.
# ============================================================
