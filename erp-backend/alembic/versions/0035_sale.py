"""Venda do Comercial: sales, sale_installments, sale_environments, sale_items
+ projects.sale_id.

Idempotente: cria cada tabela so se nao existir (inspector). Sem coluna
Boolean -> sem pitfall de server_default numerico no Postgres. A FK de
projects.sale_id fica apenas no modelo SQLAlchemy (padrao 0011): a coluna e
adicionada sem constraint, o ORM cuida da integridade.
"""

from alembic import op
import sqlalchemy as sa

revision = "0035_sale"
down_revision = "0034_account_plan"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "sales" not in tables:
        op.create_table(
            "sales",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False, unique=True),
            sa.Column("client_id", sa.String(36), nullable=False),
            sa.Column("seller_id", sa.String(36), nullable=True),
            sa.Column("partner_id", sa.String(36), nullable=True),
            sa.Column("lead_source", sa.String(120), nullable=True, server_default=""),
            sa.Column("sale_date", sa.Date(), nullable=False),
            sa.Column("total_value", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
            sa.Column("down_payment", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
            sa.Column("installments", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("installment_value", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
            sa.Column("bank_account_id", sa.String(36), nullable=True),
            sa.Column("address", sa.Text(), nullable=True, server_default=""),
            sa.Column("delivery_date", sa.Date(), nullable=True),
            sa.Column("concluded_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(80), nullable=True, server_default=""),
        )
        op.create_index("ix_sales_client_id", "sales", ["client_id"])
        op.create_index("ix_sales_seller_id", "sales", ["seller_id"])
        op.create_index("ix_sales_partner_id", "sales", ["partner_id"])
        op.create_index("ix_sales_bank_account_id", "sales", ["bank_account_id"])
        op.create_index("ix_sales_concluded_at", "sales", ["concluded_at"])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "sale_installments" not in tables:
        op.create_table(
            "sale_installments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("sale_id", sa.String(36), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("value", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
            sa.Column("status", sa.String(10), nullable=False, server_default="PENDENTE"),
            sa.Column("financial_record_id", sa.String(36), nullable=True),
        )
        op.create_index("ix_sale_installments_sale_id", "sale_installments", ["sale_id"])
        op.create_index("ix_sale_installments_financial_record_id", "sale_installments", ["financial_record_id"])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "sale_environments" not in tables:
        op.create_table(
            "sale_environments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("sale_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
        )
        op.create_index("ix_sale_environments_sale_id", "sale_environments", ["sale_id"])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "sale_items" not in tables:
        op.create_table(
            "sale_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("sale_id", sa.String(36), nullable=False),
            sa.Column("product_id", sa.String(36), nullable=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("quantity", sa.Numeric(14, 3), nullable=False, server_default=sa.text("1")),
            sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        )
        op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])
        op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"])

    # projects.sale_id — padrao 0011 (coluna sem FK no banco; FK so no modelo)
    cols = [c["name"] for c in sa.inspect(op.get_bind()).get_columns("projects")]
    if "sale_id" not in cols:
        op.add_column("projects", sa.Column("sale_id", sa.String(36), nullable=True))
        try:
            op.create_index("ix_projects_sale_id", "projects", ["sale_id"])
        except Exception:
            pass


def downgrade():
    op.execute("DROP TABLE IF EXISTS sale_installments;")
    op.execute("DROP TABLE IF EXISTS sale_environments;")
    op.execute("DROP TABLE IF EXISTS sale_items;")
    op.execute("DROP TABLE IF EXISTS sales;")
    try:
        op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS sale_id;")
    except Exception:
        pass