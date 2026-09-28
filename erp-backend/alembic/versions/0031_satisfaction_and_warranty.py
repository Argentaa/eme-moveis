"""Pesquisa de satisfacao e garantia dos projetos (idempotente).

Cria `satisfaction_surveys` e adiciona `warranty_months`/`warranty_until` em
`projects`. A garantia e derivada em dois lugares: o botao de concluir projeto
grava `warranty_until = concluded_at + warranty_months` (no blueprint) e a
leitura da API deriva `in_warranty` comparando a data com hoje — nunca pelo
nome de coluna do funil (a chave CONCLUIDO ja provou ser uma armadilha).
"""
from alembic import op

revision = "0031_satisfaction_and_warranty"
down_revision = "0030_concluded_sales_closed_at"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS satisfaction_surveys (
            id          VARCHAR(36)  NOT NULL PRIMARY KEY,
            client_id   VARCHAR(36)  NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            project_id  VARCHAR(36)  NULL REFERENCES projects(id) ON DELETE SET NULL,
            ticket_id   VARCHAR(36)  NULL REFERENCES service_tickets(id) ON DELETE SET NULL,
            score       INTEGER      NULL,
            comment     TEXT         NULL DEFAULT '',
            sent_at     TIMESTAMP    NOT NULL,
            answered_at TIMESTAMP    NULL,
            created_at  TIMESTAMP    NOT NULL
        );
        """
    )
    for nome, colunas in (
        ("ix_satisfaction_surveys_client_id", ["client_id"]),
        ("ix_satisfaction_surveys_project_id", ["project_id"]),
    ):
        try:
            op.create_index(nome, "satisfaction_surveys", colunas)
        except Exception:
            pass
    for col, ddl in (
        ("warranty_months", "ALTER TABLE projects ADD COLUMN warranty_months INTEGER NULL DEFAULT 0;"),
        ("warranty_until", "ALTER TABLE projects ADD COLUMN warranty_until DATE NULL;"),
    ):
        try:
            op.execute(ddl)
        except Exception:
            pass  # coluna ja existe (idempotente)


def downgrade():
    for col in ("warranty_until", "warranty_months"):
        try:
            op.execute(f"ALTER TABLE projects DROP COLUMN {col};")
        except Exception:
            pass
    for nome in ("ix_satisfaction_surveys_client_id", "ix_satisfaction_surveys_project_id"):
        try:
            op.drop_index(nome, table_name="satisfaction_surveys")
        except Exception:
            pass
    op.execute("DROP TABLE IF EXISTS satisfaction_surveys;")