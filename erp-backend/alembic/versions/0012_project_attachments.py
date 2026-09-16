"""Anexos por projeto: attachments.project_id (nullable, sem FK formal)."""

from alembic import op
import sqlalchemy as sa

revision = "0012_project_attachments"
down_revision = "0011_bank_accounts"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    # idempotente: adiciona coluna project_id em attachments se ainda nao existir
    try:
        op.execute("ALTER TABLE attachments ADD COLUMN IF NOT EXISTS project_id VARCHAR(36);")
    except Exception:
        try:
            cols = [c["name"] for c in insp.get_columns("attachments")]
            if "project_id" not in cols:
                op.execute("ALTER TABLE attachments ADD COLUMN project_id VARCHAR(36);")
        except Exception:
            pass


def downgrade():
    op.execute("ALTER TABLE attachments DROP COLUMN IF EXISTS project_id;")
