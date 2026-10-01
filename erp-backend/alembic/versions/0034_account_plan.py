"""Plano de contas: categorias DRE + contas (importacao do sistema legado).

Tabelas novas (nada existente e tocado):
- account_categories: as 14 categorias (codigo, descricao, indicador CREDITO/DEBITO, faixa DRE).
- account_plans: as 54 contas (codigo, codigo estruturado X.Y, descricao, categoria).

Idempotente: cria cada tabela so se nao existir (inspector).
Sem coluna Boolean -> sem pitfall de server_default no Postgres.
"""

from alembic import op
import sqlalchemy as sa

revision = "0034_account_plan"
down_revision = "0033_whatsapp_remote_jid"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "account_categories" not in tables:
        op.create_table(
            "account_categories",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.Integer(), nullable=False, unique=True),
            sa.Column("description", sa.String(120), nullable=False),
            sa.Column("indicator", sa.String(10), nullable=False, server_default="DEBITO"),
            sa.Column("dre_range", sa.String(60), nullable=True, server_default=""),
        )

    # re-inspeciona: o banco pode ter sido criado por create_all() sem alembic_version
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "account_plans" not in tables:
        op.create_table(
            "account_plans",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.Integer(), nullable=False, unique=True),
            sa.Column("structured_code", sa.String(20), nullable=False, unique=True),
            sa.Column("description", sa.String(160), nullable=False),
            sa.Column(
                "category_id",
                sa.String(36),
                sa.ForeignKey("account_categories.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
        )


def downgrade():
    op.execute("DROP TABLE IF EXISTS account_plans;")
    op.execute("DROP TABLE IF EXISTS account_categories;")
