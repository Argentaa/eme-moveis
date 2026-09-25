"""Conclusao explicita de projeto e de venda (idempotente).

Antes nao havia como dizer "este projeto acabou" sem depender do nome/chave da
coluna do funil — e isso quebra neste cliente: as colunas foram renomeadas e a
chave "CONCLUIDO" ficou numa coluna do MEIO do funil de Producao (rotulo
"Medicao In Loco"), enquanto a ultima coluna e "Entrega e pos-venda"
(ENTREGA_E_POS_VENDA). Deduzir conclusao da chave marcava projeto em medicao
como finalizado.

Agora a conclusao e um estado proprio, gravado por botao explicito:
  - projects.concluded_at      -> projeto concluido, sai da Producao e entra na
                                  aba "Projetos entregues" do Pos-venda
  - clients.sale_concluded_at  -> venda concluida, o card sai do funil de
                                  vendas e o projeto nasce na Producao

Backfill: projetos que JA estao na ultima coluna do proprio funil sao marcados
como concluidos, senao os entregues que ja existem ficariam invisiveis na aba
nova. E um mapeamento de uma vez so, nao uma regra viva — a regra viva e o
botao.
"""
from alembic import op

revision = "0028_concluded_flags"
down_revision = "0027_clients_seller"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS concluded_at TIMESTAMP NULL;")
    try:
        op.create_index("ix_projects_concluded_at", "projects", ["concluded_at"])
    except Exception:
        pass  # indice ja existe

    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS sale_concluded_at TIMESTAMP NULL;")
    try:
        op.create_index("ix_clients_sale_concluded_at", "clients", ["sale_concluded_at"])
    except Exception:
        pass  # indice ja existe

    # Backfill unico: quem ja esta na ultima coluna do proprio funil conta como
    # concluido. So preenche onde ainda esta NULL, entao reexecutar e no-op.
    op.execute(
        """
        UPDATE projects p
           SET concluded_at = now()
         WHERE p.concluded_at IS NULL
           AND p.funnel_id IS NOT NULL
           AND p.status = (
                 SELECT c.column_key
                   FROM funnel_columns c
                  WHERE c.funnel_id = p.funnel_id
                  ORDER BY c.position DESC, c.column_key DESC
                  LIMIT 1
               );
        """
    )


def downgrade():
    for tabela, indice in (
        ("projects", "ix_projects_concluded_at"),
        ("clients", "ix_clients_sale_concluded_at"),
    ):
        try:
            op.drop_index(indice, table_name=tabela)
        except Exception:
            pass
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS concluded_at;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS sale_concluded_at;")
