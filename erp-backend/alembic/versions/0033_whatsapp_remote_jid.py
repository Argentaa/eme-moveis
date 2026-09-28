"""Chat WhatsApp: remote_jid p/ buscar midia recebida sob demanda (idempotente)."""

from alembic import op
import sqlalchemy as sa

revision = "0033_whatsapp_remote_jid"
down_revision = "0032_whatsapp_chat"
branch_labels = None
depends_on = None


def upgrade():
    cols = [c["name"] for c in sa.inspect(op.get_bind()).get_columns("whatsapp_messages")]
    if "remote_jid" not in cols:
        op.add_column("whatsapp_messages",
                      sa.Column("remote_jid", sa.String(120), nullable=True))


def downgrade():
    cols = [c["name"] for c in sa.inspect(op.get_bind()).get_columns("whatsapp_messages")]
    if "remote_jid" in cols:
        op.drop_column("whatsapp_messages", "remote_jid")
