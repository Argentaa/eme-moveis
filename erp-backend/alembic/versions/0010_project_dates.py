"""Datas de producao e semaforo de prazos."""
from alembic import op

revision = "0010_project_dates"
down_revision = "0009_production"
branch_labels = None
depends_on = None

PROJECT_DATE_COLUMNS = [
    "ADD COLUMN IF NOT EXISTS start_date DATE",
    "ADD COLUMN IF NOT EXISTS planned_end_date DATE",
    "ADD COLUMN IF NOT EXISTS actual_end_date DATE",
]


def upgrade():
    for col in PROJECT_DATE_COLUMNS:
        op.execute(f"ALTER TABLE projects {col};")


def downgrade():
    for col in ["start_date", "planned_end_date", "actual_end_date"]:
        op.execute(f"ALTER TABLE projects DROP COLUMN IF EXISTS {col};")
