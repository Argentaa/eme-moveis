"""CRM Expansion: interacoes, anexos, fontes de lead, campanhas, produtos e itens de negociacao."""
from alembic import op

revision = "0002_crm_expansion"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id VARCHAR(36) PRIMARY KEY, client_id VARCHAR(36) NOT NULL,
            type VARCHAR(30) NOT NULL DEFAULT 'OBSERVACAO', content TEXT NOT NULL,
            created_by VARCHAR(80), automatic BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL,
            CONSTRAINT fk_interactions_client FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS attachments (
            id VARCHAR(36) PRIMARY KEY, client_id VARCHAR(36) NOT NULL,
            filename VARCHAR(255) NOT NULL, stored_name VARCHAR(80) NOT NULL UNIQUE,
            mime_type VARCHAR(120), size INTEGER NOT NULL DEFAULT 0,
            created_by VARCHAR(80), created_at TIMESTAMP NOT NULL,
            CONSTRAINT fk_attachments_client FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS lead_sources (
            id VARCHAR(36) PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP NOT NULL
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id VARCHAR(36) PRIMARY KEY, name VARCHAR(120) NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id VARCHAR(36) PRIMARY KEY, name VARCHAR(200) NOT NULL UNIQUE,
            description TEXT, default_price NUMERIC(14,2), unit VARCHAR(20),
            active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP NOT NULL
        );
        CREATE TABLE IF NOT EXISTS negotiation_items (
            id VARCHAR(36) PRIMARY KEY, client_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36), name VARCHAR(200) NOT NULL,
            quantity NUMERIC(14,3) NOT NULL DEFAULT 1,
            unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
            recurrence VARCHAR(30) NOT NULL DEFAULT 'UNICO',
            created_at TIMESTAMP NOT NULL,
            CONSTRAINT fk_ni_client FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
            CONSTRAINT fk_ni_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS ix_interactions_client_id ON interactions (client_id);
        CREATE INDEX IF NOT EXISTS ix_attachments_client_id ON attachments (client_id);
        CREATE INDEX IF NOT EXISTS ix_negotiation_items_client_id ON negotiation_items (client_id);
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='clients' AND column_name='campaign') THEN
                ALTER TABLE clients ADD COLUMN campaign VARCHAR(120);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS negotiation_items; DROP TABLE IF EXISTS products;"
               " DROP TABLE IF EXISTS interactions; DROP TABLE IF EXISTS attachments;"
               " DROP TABLE IF EXISTS lead_sources; DROP TABLE IF EXISTS campaigns;"
               " ALTER TABLE clients DROP COLUMN IF EXISTS campaign;")