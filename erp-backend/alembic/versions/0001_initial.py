"""Initial ERP EME Moveis: todas as tabelas."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False, server_default=""),
        sa.Column("email", sa.String(160), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="ESTOQUE"),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("avatar", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(160), nullable=True),
        sa.Column("phone", sa.String(60), nullable=True),
        sa.Column("cpf_cnpj", sa.String(30), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("funnel_status", sa.String(20), nullable=False, server_default="PROSPECCAO"),
        sa.Column("lost_reason", sa.Text(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("lead_source", sa.String(120), nullable=True),
    )
    op.create_index("ix_clients_cpf_cnpj", "clients", ["cpf_cnpj"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ORCAMENTO"),
        sa.Column("value", sa.Numeric(14, 2), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "financial_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("category", sa.String(120), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="PENDENTE"),
        sa.Column("due_date", sa.Date(), nullable=True),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_type", sa.String(20), nullable=False, server_default="STOCK"),
        sa.UniqueConstraint("name", "category_type", name="uq_category_name_type"),
    )

    op.create_table(
        "stock_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("min_quantity", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=True),
        sa.Column("supplier", sa.String(200), nullable=True),
    )
    op.create_index("ix_stock_items_sku", "stock_items", ["sku"], unique=True)

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("stock_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(80), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(30), nullable=False, server_default="PERSONALIZADO"),
        sa.Column("status", sa.String(20), nullable=False, server_default="AGENDADO"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(30), nullable=False, server_default="GERAL"),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "funnel_columns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("column_key", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="CRM"),
        sa.UniqueConstraint("column_key", "type", name="uq_funnel_key_type"),
    )

    op.create_table(
        "recurring_financial",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("category", sa.String(120), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="MENSAL"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    for table in (
        "recurring_financial", "funnel_columns", "notifications", "calendar_events",
        "stock_movements", "stock_items", "categories", "financial_records",
        "projects", "clients", "users",
    ):
        op.drop_table(table)
