"""Contas bancarias com saldo computado."""

from alembic import op
import sqlalchemy as sa

revision = "0011_bank_accounts"
down_revision = "0010_project_dates"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "bank_accounts" not in tables:
        op.create_table(
            "bank_accounts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("bank", sa.String(80), nullable=False, server_default=""),
            sa.Column("agency", sa.String(40), nullable=True, server_default=""),
            sa.Column("account_number", sa.String(60), nullable=True, server_default=""),
            sa.Column("account_type", sa.String(20), nullable=False, server_default="CORRENTE"),
            sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
            sa.Column("opening_date", sa.Date(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("low_balance_threshold", sa.Numeric(14, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # coluna em financial_records - idempotente via ADD COLUMN IF NOT EXISTS (Postgres/SQLite)
    try:
        op.execute("ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS bank_account_id VARCHAR(36);")
    except Exception:
        # fallback para sqlite sem IF NOT EXISTS (verifica via inspector)
        try:
            cols = [c["name"] for c in insp.get_columns("financial_records")]
            if "bank_account_id" not in cols:
                op.execute("ALTER TABLE financial_records ADD COLUMN bank_account_id VARCHAR(36);")
        except Exception:
            pass


def downgrade():
    op.execute("ALTER TABLE financial_records DROP COLUMN IF EXISTS bank_account_id;")
    op.execute("DROP TABLE IF EXISTS bank_accounts;")
