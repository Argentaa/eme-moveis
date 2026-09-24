"""Vendedor responsavel pelo cliente: clients.seller_id (idempotente).

A comissao de vendedor nao tinha como ser calculada: o cliente guardava o
parceiro indicador (`partner_id`) mas nao quem vendeu. Sem isso, "comissao por
vendedor" so poderia ser o total da empresa dividido entre todos — numero
inventado. O campo entra nullable: os clientes que ja existem ficam sem
vendedor e aparecem como "sem atribuicao" no relatorio, em vez de entrarem
calados na conta de alguem.
"""
from alembic import op

revision = "0027_clients_seller"
down_revision = "0026_commission_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS seller_id VARCHAR(36) "
        "REFERENCES users(id) ON DELETE SET NULL;"
    )
    try:
        op.create_index("ix_clients_seller_id", "clients", ["seller_id"])
    except Exception:
        pass  # indice ja existe


def downgrade():
    try:
        op.drop_index("ix_clients_seller_id", table_name="clients")
    except Exception:
        pass
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS seller_id;")
