"""Parceiros/Arquitetos + client.partner_id (idempotente)."""
from alembic import op
import sqlalchemy as sa

revision = "0014_partners"
down_revision = "0013_checklists"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    idx = set()
    for tname in tables:
        try:
            for i in insp.get_indexes(tname):
                if i.get("name"):
                    idx.add(i["name"])
        except Exception:
            pass

    if "partners" not in tables:
        op.create_table(
            "partners",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("office", sa.String(160), nullable=True, server_default=""),
            sa.Column("phone", sa.String(60), nullable=True, server_default=""),
            sa.Column("email", sa.String(160), nullable=True, server_default=""),
            sa.Column("city", sa.String(120), nullable=True, server_default=""),
            sa.Column("notes", sa.Text(), nullable=True, server_default=""),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("partners")

    # coluna partner_id em clients idempotente via ADD COLUMN IF NOT EXISTS
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS partner_id VARCHAR(36);")
    # indice opcional (idempotente)
    try:
        op.create_index("ix_clients_partner_id", "clients", ["partner_id"])
    except Exception:
        pass


def downgrade():
    try:
        op.drop_index("ix_clients_partner_id", table_name="clients")
    except Exception:
        pass
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS partner_id;")
    op.drop_table("partners")
