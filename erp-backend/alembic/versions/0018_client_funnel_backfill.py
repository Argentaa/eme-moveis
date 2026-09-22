"""Backfill: clientes legados sem funil vao para o funil CRM padrao (idempotente).

A partir desta versao o cadastro central (Clientes/Fornecedores) pode criar
cliente com funnel_id NULL (so cadastro, fora do funil). Os registros antigos
que estavam sem funil por outros motivos sao vinculados ao funil padrao para
preservar a visibilidade que tinham no Comercial.
"""
from alembic import op

revision = "0018_client_funnel_backfill"
down_revision = "0017_supplier_client_mirror"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE clients SET funnel_id = (
            SELECT id FROM funnels WHERE kind = 'CRM' AND is_default IS TRUE LIMIT 1
        ) WHERE funnel_id IS NULL AND EXISTS (
            SELECT 1 FROM funnels WHERE kind = 'CRM' AND is_default IS TRUE
        );
    """)


def downgrade():
    pass
