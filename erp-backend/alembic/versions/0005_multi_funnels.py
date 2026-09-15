"""Multiplos funis: funnels + colunas dinamicas + funnel_id em clients/projects."""
from alembic import op

revision = "0005_multi_funnels"
down_revision = "0004_financial_expansion"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS funnels (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            kind VARCHAR(20) NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL
        );
        """
    )
    op.execute(
        """
        INSERT INTO funnels (id, name, kind, is_default, active, created_at)
        VALUES ('funnel-default-crm', 'Funil de Vendas', 'CRM', TRUE, TRUE, NOW())
        ON CONFLICT (id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO funnels (id, name, kind, is_default, active, created_at)
        VALUES ('funnel-default-projects', 'Funil de Produção', 'PROJECTS', TRUE, TRUE, NOW())
        ON CONFLICT (id) DO NOTHING;
        """
    )
    op.execute("ALTER TABLE funnel_columns ADD COLUMN IF NOT EXISTS funnel_id VARCHAR(36);")
    op.execute("ALTER TABLE funnel_columns ADD COLUMN IF NOT EXISTS position INTEGER NOT NULL DEFAULT 0;")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS funnel_id VARCHAR(36);")
    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS funnel_id VARCHAR(36);")
    op.execute(
        """
        UPDATE funnel_columns SET funnel_id = CASE WHEN type='PROJECTS' THEN 'funnel-default-projects' ELSE 'funnel-default-crm' END WHERE funnel_id IS NULL;
        """
    )
    op.execute("ALTER TABLE funnel_columns DROP CONSTRAINT IF EXISTS uq_funnel_key_type;")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_funnel_column_key ON funnel_columns (funnel_id, column_key);")
    op.execute("UPDATE clients SET funnel_id = 'funnel-default-crm' WHERE funnel_id IS NULL;")
    op.execute("UPDATE projects SET funnel_id = 'funnel-default-projects' WHERE funnel_id IS NULL;")


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_funnel_column_key;")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS funnel_id;")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS funnel_id;")
    op.execute("ALTER TABLE funnel_columns DROP COLUMN IF EXISTS funnel_id;")
    op.execute("ALTER TABLE funnel_columns DROP COLUMN IF EXISTS position;")
    op.execute("DROP TABLE IF EXISTS funnels;")
