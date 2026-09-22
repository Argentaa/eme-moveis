"""Cadastro central: clientes podem ser fornecedores (idempotente).

Adiciona campos de fornecedor na tabela clients (is_supplier + dados de
compra). Nao migra dados da tabela suppliers — o merge e feito em consulta
(endpoint /api/vendors).
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_client_supplier_fields"
down_revision = "0015_changelog_reads"
branch_labels = None
depends_on = None


def upgrade():
    # Colunas novas em clients — idempotente via ADD COLUMN IF NOT EXISTS (PG).
    # NOTA: is_supplier usa server_default sa.false() (boolean) — pitfall PG:
    # server_default=sa.text("0")/("1") gera DEFAULT 0/1 (inteiro) e o PG rejeita.
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_supplier BOOLEAN NOT NULL DEFAULT FALSE;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS contact VARCHAR(160) NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS category VARCHAR(80) NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(120) NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS avg_delivery_days INTEGER;")
    try:
        op.create_index("ix_clients_is_supplier", "clients", ["is_supplier"])
    except Exception:
        pass


def downgrade():
    try:
        op.drop_index("ix_clients_is_supplier", table_name="clients")
    except Exception:
        pass
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS avg_delivery_days;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS payment_terms;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS category;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS contact;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS is_supplier;")