"""Compras: purchase_orders + purchase_items com FKs idempotentes."""

from alembic import op
import sqlalchemy as sa

revision = "0006_purchases"
down_revision = "0005_multi_funnels"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    idx = set()
    for tname in tables:
        for i in insp.get_indexes(tname):
            if i.get("name"):
                idx.add(i["name"])

    if "purchase_orders" not in tables:
        op.create_table(
            "purchase_orders",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("number", sa.String(20), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="SOLICITADA"),
            sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("request_date", sa.Date(), nullable=False),
            sa.Column("expected_date", sa.Date(), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "ix_purchase_orders_supplier_id" not in idx:
        try:
            op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
        except Exception:
            pass

    if "purchase_items" not in tables:
        op.create_table(
            "purchase_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("order_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("stock_item_id", sa.String(36), sa.ForeignKey("stock_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("material_name", sa.String(200), nullable=False),
            sa.Column("quantity", sa.Numeric(14, 3), nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("received_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        )
    if "ix_purchase_items_order_id" not in idx:
        try:
            op.create_index("ix_purchase_items_order_id", "purchase_items", ["order_id"])
        except Exception:
            pass
    if "ix_purchase_items_stock_item_id" not in idx:
        try:
            op.create_index("ix_purchase_items_stock_item_id", "purchase_items", ["stock_item_id"])
        except Exception:
            pass


def downgrade():
    op.drop_index("ix_purchase_items_stock_item_id", table_name="purchase_items")
    op.drop_index("ix_purchase_items_order_id", table_name="purchase_items")
    op.drop_index("ix_purchase_orders_supplier_id", table_name="purchase_orders")
    op.drop_table("purchase_items")
    op.drop_table("purchase_orders")
