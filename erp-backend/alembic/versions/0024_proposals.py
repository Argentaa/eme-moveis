"""Propostas comerciais: proposals + proposal_items.

O ERP nao tinha proposta nenhuma — o vendedor montava o orcamento fora do
sistema e o cliente nunca via um documento com numero proprio. Aqui entra a
proposta com itens (descricao, quantidade, preco) e o total calculado.

`project_id` e nullable: a proposta nasce antes do projeto (so vira projeto
quando o cliente aceita). `sent_channel` guarda por onde saiu (WHATSAPP/WA_ME/
MANUAL), para o comercial saber o que foi realmente enviado.

Numeracao: o plano chamava esta de 0021; o encadeamento real vem de
0023_logistics, entao ela e a 0024.
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_proposals"
down_revision = "0023_logistics"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "proposals" not in tables:
        op.create_table(
            "proposals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("number", sa.String(40), nullable=False),
            sa.Column("client_id", sa.String(36),
                      sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", sa.String(36),
                      sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="RASCUNHO"),
            sa.Column("total_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("valid_until", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("sent_channel", sa.String(20), nullable=True),
            sa.Column("created_by", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("proposals")

    if "proposal_items" not in tables:
        op.create_table(
            "proposal_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("proposal_id", sa.String(36),
                      sa.ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False),
            sa.Column("description", sa.String(255), nullable=False),
            sa.Column("quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        tables.add("proposal_items")

    for name, table, col in (
        ("ix_proposals_client_id", "proposals", "client_id"),
        ("ix_proposals_project_id", "proposals", "project_id"),
        ("ix_proposals_status", "proposals", "status"),
        ("ix_proposal_items_proposal_id", "proposal_items", "proposal_id"),
    ):
        try:
            op.create_index(name, table, [col])
        except Exception:
            pass  # indice ja existe


def downgrade():
    for name, table in (
        ("ix_proposal_items_proposal_id", "proposal_items"),
        ("ix_proposals_status", "proposals"),
        ("ix_proposals_project_id", "proposals"),
        ("ix_proposals_client_id", "proposals"),
    ):
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass
    op.execute("DROP TABLE IF EXISTS proposal_items;")
    op.execute("DROP TABLE IF EXISTS proposals;")
