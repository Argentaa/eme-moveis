"""Fornecedor rico: categoria, condicoes de pagamento e prazo medio."""
from alembic import op

revision = "0007_supplier_enrich"
down_revision = "0006_purchases"
branch_labels = None
depends_on = None

SUPPLIER_COLUMNS = [
    "ADD COLUMN IF NOT EXISTS address TEXT",
    "ADD COLUMN IF NOT EXISTS category VARCHAR(80)",
    "ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(120)",
    "ADD COLUMN IF NOT EXISTS avg_delivery_days INTEGER",
]


def upgrade():
    for col in SUPPLIER_COLUMNS:
        op.execute(f"ALTER TABLE suppliers {col};")


def downgrade():
    for col in ["address", "category", "payment_terms", "avg_delivery_days"]:
        op.execute(f"ALTER TABLE suppliers DROP COLUMN IF EXISTS {col};")
