"""Alarga clients.funnel_status e projects.status para VARCHAR(60) (idempotente).

FunnelColumn.column_key tem ate 60 chars (ex.: PROPOSTA_EM_ELABORACAO, 22).
Com VARCHAR(20), vincular/mover cliente ou projeto para uma etapa com chave
longa quebrava no Postgres (StringDataRightTruncation, 500) — no SQLite os
testes nunca pegavam porque ele nao impõe o limite.
"""
from alembic import op

revision = "0019_status_width_60"
down_revision = "0018_client_funnel_backfill"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE clients ALTER COLUMN funnel_status TYPE VARCHAR(60);")
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(60);")


def downgrade():
    op.execute("ALTER TABLE clients ALTER COLUMN funnel_status TYPE VARCHAR(20);")
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(20);")
