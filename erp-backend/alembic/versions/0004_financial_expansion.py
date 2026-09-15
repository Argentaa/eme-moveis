"""Expansao financeira: colunas contabeis em financial_records, fornecedores e orcamento."""
from alembic import op

revision = "0004_financial_expansion"
down_revision = "0003_changelog"
branch_labels = None
depends_on = None

FIN_COLUMNS = [
    "ADD COLUMN IF NOT EXISTS doc_number VARCHAR(60)",
    "ADD COLUMN IF NOT EXISTS issue_date DATE",
    "ADD COLUMN IF NOT EXISTS doc_type VARCHAR(20) NOT NULL DEFAULT ''",
    "ADD COLUMN IF NOT EXISTS bank VARCHAR(80)",
    "ADD COLUMN IF NOT EXISTS account_plan VARCHAR(120)",
    "ADD COLUMN IF NOT EXISTS item_description TEXT",
    "ADD COLUMN IF NOT EXISTS installments INTEGER NOT NULL DEFAULT 1",
    "ADD COLUMN IF NOT EXISTS client_id VARCHAR(36)",
    "ADD COLUMN IF NOT EXISTS supplier_id VARCHAR(36)",
    "ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN NOT NULL DEFAULT FALSE",
]


def upgrade():
    for col in FIN_COLUMNS:
        op.execute("ALTER TABLE financial_records " + col + ";")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            cnpj VARCHAR(30),
            contact VARCHAR(160),
            phone VARCHAR(60),
            email VARCHAR(160),
            created_at TIMESTAMP NOT NULL
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_goals (
            id VARCHAR(36) PRIMARY KEY,
            year INTEGER NOT NULL,
            month INTEGER,
            category VARCHAR(120) NOT NULL,
            target_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL
        );
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS budget_goals;")
    op.execute("DROP TABLE IF EXISTS suppliers;")
    for col in [
        "doc_number", "issue_date", "doc_type", "bank", "account_plan",
        "item_description", "installments", "client_id", "supplier_id", "is_recurring",
    ]:
        op.execute("ALTER TABLE financial_records DROP COLUMN IF EXISTS " + col + ";")