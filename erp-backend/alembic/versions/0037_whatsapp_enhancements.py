"""WhatsApp: nao-lidas, reacoes/citacao e respostas rapidas (idempotente).

- whatsapp_conversations.unread_count: contador real de nao-lidas (webhook
  incrementa; abrir/responder zera). Sem isso o badge era sempre 0.
- whatsapp_messages.reaction: emoji aplicado a mensagem.
- whatsapp_messages.reply_to_id: mensagem citada (id local).
- whatsapp_quick_replies: textos prontos do atendimento (nada na Evolution).

Idempotente: inspector para colunas e tabela; nada de Boolean com default
inteiro (pitfall PG). Roda no boot via alembic.
"""

from alembic import op
import sqlalchemy as sa

revision = "0037_whatsapp_enhancements"
down_revision = "0036_deals"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols_conv = [c["name"] for c in insp.get_columns("whatsapp_conversations")]
    if "unread_count" not in cols_conv:
        op.add_column(
            "whatsapp_conversations",
            sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
        )

    cols_msg = [c["name"] for c in insp.get_columns("whatsapp_messages")]
    if "reaction" not in cols_msg:
        op.add_column(
            "whatsapp_messages",
            sa.Column("reaction", sa.String(16), nullable=False, server_default=""),
        )
    if "reply_to_id" not in cols_msg:
        op.add_column(
            "whatsapp_messages",
            sa.Column("reply_to_id", sa.String(36), nullable=True),
        )

    if "whatsapp_quick_replies" not in set(insp.get_table_names()):
        op.create_table(
            "whatsapp_quick_replies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("title", sa.String(80), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_whatsapp_quick_replies_title",
            "whatsapp_quick_replies", ["title"], unique=True,
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "whatsapp_quick_replies" in set(insp.get_table_names()):
        op.drop_table("whatsapp_quick_replies")
    cols_msg = [c["name"] for c in insp.get_columns("whatsapp_messages")]
    if "reply_to_id" in cols_msg:
        op.drop_column("whatsapp_messages", "reply_to_id")
    if "reaction" in cols_msg:
        op.drop_column("whatsapp_messages", "reaction")
    cols_conv = [c["name"] for c in insp.get_columns("whatsapp_conversations")]
    if "unread_count" in cols_conv:
        op.drop_column("whatsapp_conversations", "unread_count")
