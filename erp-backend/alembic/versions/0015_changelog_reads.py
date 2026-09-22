"""Leitura das novidades por usuario: lido / nao lido. Idempotente."""
from alembic import op
import sqlalchemy as sa

revision = "0015_changelog_reads"
down_revision = "0014_partners"
branch_labels = None
depends_on = None


def _index_names(insp):
    names = set()
    for tname in set(insp.get_table_names()):
        try:
            for i in insp.get_indexes(tname):
                if i.get("name"):
                    names.add(i["name"])
        except Exception:
            pass
    return names


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "changelog_reads" not in tables:
        op.create_table(
            "changelog_reads",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "entry_id",
                sa.String(36),
                sa.ForeignKey("changelog_entries.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("read_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "entry_id", name="uq_changelog_read_user_entry"),
        )

    idx = _index_names(insp)
    if "ix_changelog_reads_user_id" not in idx:
        op.create_index("ix_changelog_reads_user_id", "changelog_reads", ["user_id"])
    if "ix_changelog_reads_entry_id" not in idx:
        op.create_index("ix_changelog_reads_entry_id", "changelog_reads", ["entry_id"])


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "changelog_reads" in set(insp.get_table_names()):
        op.drop_table("changelog_reads")
