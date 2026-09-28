"""Chat interno de WhatsApp (idempotente).

Cria `whatsapp_instances` (uma linha por instancia da Evolution),
`whatsapp_conversations` (uma por telefone+instancia, com link opcional
para Client) e `whatsapp_messages` (provider_id unique = dedupe do webhook).
"""
from alembic import op

revision = "0032_whatsapp_chat"
down_revision = "0031_satisfaction_and_warranty"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_instances (
            id          VARCHAR(36)  NOT NULL PRIMARY KEY,
            name        VARCHAR(80)  NOT NULL UNIQUE,
            api_key     TEXT         NULL DEFAULT '',
            status      VARCHAR(20)  NOT NULL DEFAULT 'desconectada',
            phone       VARCHAR(30)  NULL DEFAULT '',
            created_at  TIMESTAMP    NOT NULL,
            updated_at  TIMESTAMP    NOT NULL
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_conversations (
            id              VARCHAR(36)  NOT NULL PRIMARY KEY,
            instance        VARCHAR(80)  NOT NULL DEFAULT 'eme-moveis',
            phone           VARCHAR(30)  NOT NULL,
            name            VARCHAR(160) NULL DEFAULT '',
            client_id       VARCHAR(36)  NULL REFERENCES clients(id) ON DELETE SET NULL,
            last_message_at TIMESTAMP    NULL,
            created_at      TIMESTAMP    NOT NULL,
            CONSTRAINT uq_waconv_instance_phone UNIQUE (instance, phone)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id              VARCHAR(36)  NOT NULL PRIMARY KEY,
            conversation_id VARCHAR(36)  NOT NULL REFERENCES whatsapp_conversations(id) ON DELETE CASCADE,
            provider_id     VARCHAR(120) NULL UNIQUE,
            direction       VARCHAR(8)   NOT NULL DEFAULT 'in',
            kind            VARCHAR(16)  NOT NULL DEFAULT 'text',
            body            TEXT         NULL DEFAULT '',
            media_stored    VARCHAR(255) NULL,
            media_filename  VARCHAR(255) NULL,
            media_mime      VARCHAR(120) NULL,
            media_size      INTEGER      NULL,
            status          VARCHAR(20)  NOT NULL DEFAULT 'stored',
            created_by      VARCHAR(80)  NULL DEFAULT '',
            created_at      TIMESTAMP    NOT NULL
        );
        """
    )
    for nome, tabela, colunas in (
        ("ix_whatsapp_conversations_phone", "whatsapp_conversations", ["phone"]),
        ("ix_whatsapp_conversations_client_id", "whatsapp_conversations", ["client_id"]),
        ("ix_whatsapp_messages_conversation_id", "whatsapp_messages", ["conversation_id"]),
        ("ix_whatsapp_messages_provider_id", "whatsapp_messages", ["provider_id"]),
    ):
        try:
            op.create_index(nome, tabela, colunas)
        except Exception:
            pass  # indice ja existe (idempotente)


def downgrade():
    op.execute("DROP TABLE IF EXISTS whatsapp_messages;")
    op.execute("DROP TABLE IF EXISTS whatsapp_conversations;")
    op.execute("DROP TABLE IF EXISTS whatsapp_instances;")
