"""Chamados de assistencia: service_tickets + ticket_photos."""

from alembic import op
import sqlalchemy as sa

revision = "0008_tickets"
down_revision = "0007_supplier_enrich"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    idx = set()
    for tname in tables:
        for i in insp.get_indexes(tname):
            if i.get("name"):
                idx.add(i["name"])

    if "service_tickets" not in tables:
        op.create_table(
            "service_tickets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("number", sa.String(20), nullable=False, unique=True),
            sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="ABERTO"),
            sa.Column("cost", sa.Numeric(14, 2), nullable=True),
            sa.Column("cause", sa.Text(), nullable=True),
            sa.Column("solution", sa.Text(), nullable=True),
            sa.Column("in_warranty", sa.Boolean(), nullable=True),
            sa.Column("assigned_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("opened_at", sa.DateTime(), nullable=False),
            sa.Column("scheduled_at", sa.Date(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("calendar_event_id", sa.String(36), sa.ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(80), nullable=True),
        )
    if "ix_service_tickets_client_id" not in idx:
        try:
            op.create_index("ix_service_tickets_client_id", "service_tickets", ["client_id"])
        except Exception:
            pass
    if "ix_service_tickets_project_id" not in idx:
        try:
            op.create_index("ix_service_tickets_project_id", "service_tickets", ["project_id"])
        except Exception:
            pass
    if "ix_service_tickets_assigned_user_id" not in idx:
        try:
            op.create_index("ix_service_tickets_assigned_user_id", "service_tickets", ["assigned_user_id"])
        except Exception:
            pass

    if "ticket_photos" not in tables:
        op.create_table(
            "ticket_photos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("ticket_id", sa.String(36), sa.ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("stored_name", sa.String(80), nullable=False, unique=True),
            sa.Column("mime_type", sa.String(120), nullable=True),
            sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "ix_ticket_photos_ticket_id" not in idx:
        try:
            op.create_index("ix_ticket_photos_ticket_id", "ticket_photos", ["ticket_id"])
        except Exception:
            pass


def downgrade():
    try:
        op.drop_index("ix_ticket_photos_ticket_id", table_name="ticket_photos")
    except Exception:
        pass
    try:
        op.drop_index("ix_service_tickets_assigned_user_id", table_name="service_tickets")
    except Exception:
        pass
    try:
        op.drop_index("ix_service_tickets_project_id", table_name="service_tickets")
    except Exception:
        pass
    try:
        op.drop_index("ix_service_tickets_client_id", table_name="service_tickets")
    except Exception:
        pass
    op.execute("DROP TABLE IF EXISTS ticket_photos;")
    op.execute("DROP TABLE IF EXISTS service_tickets;")
