"""Campos de montagem em calendar_events: team e location (idempotente).

Montagem e um CalendarEvent de tipo MONTAGEM — nao cria tabela nova (decisao
do plano, secao 3). Faltavam so os dois campos que a spec pede na agenda de
montagens: qual equipe vai e onde e a montagem.

Numeracao: o plano chamava esta de 0022 assumindo um 0021 que nao existe no
repo. O encadeamento real vem de 0020_sales_goals, entao ela e a 0021.
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_assembly_fields"
down_revision = "0020_sales_goals"
branch_labels = None
depends_on = None


def upgrade():
    # IF NOT EXISTS porque a cadeia inteira roda a cada boot do app: a
    # migracao precisa ser no-op na segunda execucao.
    op.execute("ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS team VARCHAR(120);")
    op.execute("ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS location VARCHAR(200);")

    try:
        op.create_index("ix_calendar_events_team", "calendar_events", ["team"])
    except Exception:
        pass  # indice ja existe


def downgrade():
    try:
        op.drop_index("ix_calendar_events_team", table_name="calendar_events")
    except Exception:
        pass
    op.execute("ALTER TABLE calendar_events DROP COLUMN IF EXISTS team;")
    op.execute("ALTER TABLE calendar_events DROP COLUMN IF EXISTS location;")
