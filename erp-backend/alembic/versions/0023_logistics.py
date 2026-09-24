"""Campos logisticos em purchase_orders: carrier e tracking (idempotente).

O calendario logistico precisa saber com quem a compra vem e o codigo de
rastreio, para o cliente cobrar a transportadora sem procurar no e-mail.
"""
from alembic import op

revision = "0023_logistics"
down_revision = "0022_purchase_quotations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS carrier VARCHAR(120);")
    op.execute("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS tracking VARCHAR(120);")


def downgrade():
    op.execute("ALTER TABLE purchase_orders DROP COLUMN IF EXISTS carrier;")
    op.execute("ALTER TABLE purchase_orders DROP COLUMN IF EXISTS tracking;")
