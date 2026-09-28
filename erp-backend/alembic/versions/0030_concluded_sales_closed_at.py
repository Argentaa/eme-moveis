"""closed_at para vendas concluidas pelo botao (idempotente, so backfill).

O botao "Concluir venda" (POST /api/clients/<id>/conclude-sale) gravava so
`sale_concluded_at`: o projeto nascia na Producao, mas a venda nao entrava na
meta comercial, na comissao nem nos relatorios de CRM — todos leem
`clients.closed_at`, que so o caminho pelo funil preenchia. O codigo do botao
foi corrigido para gravar os dois; esta migracao conserta as vendas que ja
passaram pelo botao antes do fix (ex.: a de R$ 12.570 que o cliente reportou).

So preenche onde closed_at ainda esta NULL, entao reexecutar e no-op.
"""
from alembic import op

revision = "0030_concluded_sales_closed_at"
down_revision = "0029_stock_losses"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE clients
           SET closed_at = sale_concluded_at
         WHERE sale_concluded_at IS NOT NULL
           AND closed_at IS NULL;
        """
    )


def downgrade():
    # Backfill de dados: sem reverso (reverter apagaria data real).
    pass
