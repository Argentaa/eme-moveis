"""Cotacoes por compra: purchase_quotations + purchase_quotation_items.

O ERP so guardava UM fornecedor e UM preco por item de compra (purchase_items.
unit_price). A spec pede comparativo entre fornecedores: varias cotacoes para o
mesmo pedido, cada uma com seus precos por item, e uma vencedora.

Tabelas novas em vez de colunas em purchase_items porque o numero de cotacoes
por compra e variavel — nao cabe em coluna.

Numeracao: o plano chamava esta de 0023 assumindo um 0022 que virou a 0021
(campos de montagem). O encadeamento real vem de 0021_assembly_fields.
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_purchase_quotations"
down_revision = "0021_assembly_fields"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "purchase_quotations" not in tables:
        op.create_table(
            "purchase_quotations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("order_id", sa.String(36),
                      sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("supplier_id", sa.String(36),
                      sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("delivery_days", sa.Integer(), nullable=True),
            sa.Column("payment_terms", sa.String(120), nullable=True),
            sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("purchase_quotations")

    if "purchase_quotation_items" not in tables:
        op.create_table(
            "purchase_quotation_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("quotation_id", sa.String(36),
                      sa.ForeignKey("purchase_quotations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("purchase_item_id", sa.String(36),
                      sa.ForeignKey("purchase_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("purchase_quotation_items")

    for name, table, col in (
        ("ix_purchase_quotations_order_id", "purchase_quotations", "order_id"),
        ("ix_purchase_quotations_supplier_id", "purchase_quotations", "supplier_id"),
        ("ix_purchase_quotation_items_quotation_id", "purchase_quotation_items", "quotation_id"),
        ("ix_purchase_quotation_items_purchase_item_id", "purchase_quotation_items", "purchase_item_id"),
    ):
        try:
            op.create_index(name, table, [col])
        except Exception:
            pass  # indice ja existe


def downgrade():
    for name, table in (
        ("ix_purchase_quotation_items_purchase_item_id", "purchase_quotation_items"),
        ("ix_purchase_quotation_items_quotation_id", "purchase_quotation_items"),
        ("ix_purchase_quotations_supplier_id", "purchase_quotations"),
        ("ix_purchase_quotations_order_id", "purchase_quotations"),
    ):
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass
    op.drop_table("purchase_quotation_items")
    op.drop_table("purchase_quotations")
