"""Changelog (Novidades): tabela de atualizacoes do sistema."""
from alembic import op

revision = "0003_changelog"
down_revision = "0002_crm_expansion"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS changelog_entries (
            id VARCHAR(36) PRIMARY KEY, title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL, category VARCHAR(40) NOT NULL DEFAULT 'GERAL',
            entry_date DATE NOT NULL, created_by VARCHAR(80),
            created_at TIMESTAMP NOT NULL
        );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS changelog_entries;")
