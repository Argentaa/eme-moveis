"""Espelho de cliente-fornecedor: suppliers.client_id (idempotente).

Permite que um cliente marcado como fornecedor tenha uma linha espelho em
suppliers, preservando as FKs existentes (purchase_orders.supplier_id e
financial_records.supplier_id continuam apontando para suppliers.id).
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_supplier_client_mirror"
down_revision = "0016_client_supplier_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS client_id VARCHAR(36);")
    # FK para clients (SET NULL ao remover o cliente) — idempotente via bloco DO.
    op.execute("""
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_suppliers_client_id') THEN
        ALTER TABLE suppliers ADD CONSTRAINT fk_suppliers_client_id
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL;
    END IF;
END $$;
""")
    try:
        op.create_index("ix_suppliers_client_id", "suppliers", ["client_id"], unique=False)
    except Exception:
        pass


def downgrade():
    try:
        op.drop_index("ix_suppliers_client_id", table_name="suppliers")
    except Exception:
        pass
    op.execute("ALTER TABLE suppliers DROP CONSTRAINT IF EXISTS fk_suppliers_client_id;")
    op.execute("ALTER TABLE suppliers DROP COLUMN IF EXISTS client_id;")
