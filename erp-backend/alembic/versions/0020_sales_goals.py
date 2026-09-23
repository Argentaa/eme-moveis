"""Metas comerciais (sales_goals) + clients.closed_at (idempotente).

- sales_goals: meta de vendas do planejamento comercial. Separada de
  budget_goals, que e orcamento de despesa por categoria.
- clients.closed_at: data em que o cliente entrou na ultima etapa do funil.
  Sem ela nao da para calcular "vendas realizadas no mes" — o Client so tinha
  created_at, o que tornaria a meta mensal uma comparacao enganosa.
  Registros antigos ficam NULL (nao ha como reconstruir a data).
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_sales_goals"
down_revision = "0019_status_width_60"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "sales_goals" not in tables:
        op.create_table(
            "sales_goals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("month", sa.Integer(), nullable=True),
            sa.Column("scope", sa.String(20), nullable=False, server_default="GERAL"),
            sa.Column("user_id", sa.String(36),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("partner_id", sa.String(36),
                      sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=True),
            sa.Column("target_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("sales_goals")

    # data de fechamento da venda (meta comercial e, depois, comissao)
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP;")

    for name, table, col in (
        ("ix_clients_closed_at", "clients", "closed_at"),
        ("ix_sales_goals_user_id", "sales_goals", "user_id"),
        ("ix_sales_goals_partner_id", "sales_goals", "partner_id"),
    ):
        try:
            op.create_index(name, table, [col])
        except Exception:
            pass  # indice ja existe


def downgrade():
    for name, table in (
        ("ix_sales_goals_user_id", "sales_goals"),
        ("ix_sales_goals_partner_id", "sales_goals"),
        ("ix_clients_closed_at", "clients"),
    ):
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS closed_at;")
    op.drop_table("sales_goals")
