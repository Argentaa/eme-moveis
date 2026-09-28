"""Perdas e avarias de estoque (idempotente).

Cria `stock_losses`: o registro do que se perdeu ou avariou, com motivo e custo.
A tabela nao substitui o historico de movimentacoes — ela o COMPLEMENTA: gravar
uma perda decrementa `stock_items.quantity` e cria um `stock_movements` tipo
PERDA na mesma transacao (feito no blueprint, nao aqui). Assim o extrato de
movimentacoes continua contando a historia inteira do estoque, e a perda
carrega o "por que" e o "quanto custou" que a movimentacao nao tem.

`kind` e PERDA (sumiu, quebrou, venceu) ou AVARIA (danificado, ainda existe mas
nao serve) — separados porque a acao de correcao e diferente.
"""
from alembic import op

revision = "0029_stock_losses"
down_revision = "0028_concluded_flags"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_losses (
            id            VARCHAR(36)  NOT NULL PRIMARY KEY,
            stock_item_id VARCHAR(36)  NOT NULL REFERENCES stock_items(id) ON DELETE CASCADE,
            quantity      NUMERIC(14, 3) NOT NULL,
            kind          VARCHAR(10)  NOT NULL,
            reason        TEXT         NULL,
            cost          NUMERIC(14, 2) NULL DEFAULT 0,
            loss_date     DATE         NOT NULL,
            created_by    VARCHAR(80)  NULL DEFAULT '',
            created_at    TIMESTAMP    NOT NULL
        );
        """
    )
    for nome, colunas in (
        ("ix_stock_losses_stock_item_id", ["stock_item_id"]),
        ("ix_stock_losses_loss_date", ["loss_date"]),
    ):
        try:
            op.create_index(nome, "stock_losses", colunas)
        except Exception:
            pass  # indice ja existe


def downgrade():
    for nome in ("ix_stock_losses_stock_item_id", "ix_stock_losses_loss_date"):
        try:
            op.drop_index(nome, table_name="stock_losses")
        except Exception:
            pass
    op.execute("DROP TABLE IF EXISTS stock_losses;")
