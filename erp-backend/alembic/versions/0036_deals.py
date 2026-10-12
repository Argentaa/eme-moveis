"""Multi-card no funil: tabela deals (o CARD separado do CADASTRO) + deal_id
em sales/projects.

Idempotente (padrao do repo): cria a tabela so se nao existir (inspector),
adiciona as colunas so se faltarem (sem constraint FK no banco — padrao 0011:
a FK fica apenas no modelo SQLAlchemy, o ORM cuida da integridade) e o
backfill so insere o que falta (guard NOT EXISTS) — re-run e no-op.

Sem coluna Boolean -> sem pitfall de server_default numerico no Postgres.
"""

import uuid

from alembic import op
import sqlalchemy as sa

revision = "0036_deals"
down_revision = "0035_sale"
branch_labels = None
depends_on = None


def backfill(conn):
    """1 deal por cliente COM funil + liga sales/projects pelo client_id.

    Recebe uma conexao (op.get_bind() na migracao; db.session.connection()
    nos testes) para o mesmo codigo rodar nos dois mundos. Portatil PG/SQLite:
    id gerado em Python (uuid4 hex), sem funcao especifica de banco.
    """
    if "deals" not in sa.inspect(conn).get_table_names():
        return
    cand = conn.execute(sa.text(
        "SELECT c.id, c.funnel_id, c.funnel_status, c.name, c.estimated_value,"
        " c.lost_reason, c.seller_id, c.partner_id, c.lead_source, c.campaign,"
        " c.sale_concluded_at, c.closed_at, c.created_at FROM clients c"
        " WHERE c.funnel_id IS NOT NULL"
        " AND NOT EXISTS (SELECT 1 FROM deals d WHERE d.client_id = c.id"
        " AND ((d.funnel_id = c.funnel_id) OR (d.funnel_id IS NULL AND c.funnel_id IS NULL)))"
    )).mappings().fetchall()
    for r in cand:
        conn.execute(sa.text(
            "INSERT INTO deals (id, client_id, funnel_id, funnel_status, title,"
            " estimated_value, lost_reason, seller_id, partner_id, lead_source,"
            " campaign, sale_concluded_at, closed_at, created_at)"
            " VALUES (:id, :client_id, :funnel_id, :funnel_status, :title,"
            " :estimated_value, :lost_reason, :seller_id, :partner_id, :lead_source,"
            " :campaign, :sale_concluded_at, :closed_at, :created_at)"
        ), {
            "id": uuid.uuid4().hex,
            "client_id": r["id"],
            "funnel_id": r["funnel_id"],
            "funnel_status": r["funnel_status"] or "PROSPECCAO",
            "title": ("Negociacao inicial - " + (r["name"] or ""))[:200],
            "estimated_value": r["estimated_value"],
            "lost_reason": r["lost_reason"],
            "seller_id": r["seller_id"],
            "partner_id": r["partner_id"],
            "lead_source": r["lead_source"] or "",
            "campaign": r["campaign"] or "",
            "sale_concluded_at": r["sale_concluded_at"],
            "closed_at": r["closed_at"],
            "created_at": r["created_at"],
        })
    conn.execute(sa.text(
        "UPDATE sales SET deal_id = (SELECT d.id FROM deals d"
        " WHERE d.client_id = sales.client_id LIMIT 1) WHERE deal_id IS NULL"
    ))
    conn.execute(sa.text(
        "UPDATE projects SET deal_id = (SELECT d.id FROM deals d"
        " WHERE d.client_id = projects.client_id LIMIT 1)"
        " WHERE deal_id IS NULL AND client_id IS NOT NULL"
    ))


def upgrade():
    bind = op.get_bind()
    if "deals" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "deals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("client_id", sa.String(36), nullable=False),
            sa.Column("funnel_id", sa.String(36), nullable=True),
            sa.Column("funnel_status", sa.String(60), nullable=False, server_default="PROSPECCAO"),
            sa.Column("title", sa.String(200), nullable=False, server_default=""),
            sa.Column("estimated_value", sa.Numeric(14, 2), nullable=True),
            sa.Column("lost_reason", sa.Text(), nullable=True),
            sa.Column("seller_id", sa.String(36), nullable=True),
            sa.Column("partner_id", sa.String(36), nullable=True),
            sa.Column("lead_source", sa.String(120), nullable=True, server_default=""),
            sa.Column("campaign", sa.String(120), nullable=True, server_default=""),
            sa.Column("sale_concluded_at", sa.DateTime(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_deals_client_id", "deals", ["client_id"])
        op.create_index("ix_deals_funnel_status", "deals", ["funnel_id", "funnel_status"])
        op.create_index("ix_deals_closed_at", "deals", ["closed_at"])

    for table in ("sales", "projects"):
        cols = [c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)]
        if "deal_id" not in cols:
            op.add_column(table, sa.Column("deal_id", sa.String(36), nullable=True))
            try:
                op.create_index("ix_%s_deal_id" % table, table, ["deal_id"])
            except Exception:
                pass

    backfill(op.get_bind())


def downgrade():
    for table in ("sales", "projects"):
        try:
            op.execute("ALTER TABLE %s DROP COLUMN IF EXISTS deal_id;" % table)
        except Exception:
            pass
    op.execute("DROP TABLE IF EXISTS deals;")
