"""Producao industrial: ambientes, trabalhadores, maquinas, apontamentos e perdas."""

from alembic import op
import sqlalchemy as sa

revision = "0009_production"
down_revision = "0008_tickets"
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

    if "project_environments" not in tables:
        op.create_table(
            "project_environments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("env_type", sa.String(30), nullable=False, server_default="OUTRO"),
            sa.Column("area_m2", sa.Numeric(10, 2), nullable=True),
            sa.Column("value", sa.Numeric(14, 2), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="PLANEJADO"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "ix_project_environments_project_id" not in idx:
        try:
            op.create_index("ix_project_environments_project_id", "project_environments", ["project_id"])
        except Exception:
            pass

    if "workers" not in tables:
        op.create_table(
            "workers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(160), nullable=False, unique=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    # workers name unique: already via unique=True; ensure index if needed
    if "machines" not in tables:
        op.create_table(
            "machines",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(160), nullable=False, unique=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if "time_entries" not in tables:
        op.create_table(
            "time_entries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("environment_id", sa.String(36), sa.ForeignKey("project_environments.id", ondelete="SET NULL"), nullable=True),
            sa.Column("worker_id", sa.String(36), sa.ForeignKey("workers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("machine_id", sa.String(36), sa.ForeignKey("machines.id", ondelete="SET NULL"), nullable=True),
            sa.Column("hours", sa.Numeric(6, 2), nullable=False, server_default="0"),
            sa.Column("hours_type", sa.String(20), nullable=False, server_default="PRODUTIVA"),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "ix_time_entries_project_id" not in idx:
        try:
            op.create_index("ix_time_entries_project_id", "time_entries", ["project_id"])
        except Exception:
            pass
    if "ix_time_entries_environment_id" not in idx:
        try:
            op.create_index("ix_time_entries_environment_id", "time_entries", ["environment_id"])
        except Exception:
            pass
    if "ix_time_entries_worker_id" not in idx:
        try:
            op.create_index("ix_time_entries_worker_id", "time_entries", ["worker_id"])
        except Exception:
            pass
    if "ix_time_entries_machine_id" not in idx:
        try:
            op.create_index("ix_time_entries_machine_id", "time_entries", ["machine_id"])
        except Exception:
            pass

    if "production_issues" not in tables:
        op.create_table(
            "production_issues",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("worker_id", sa.String(36), sa.ForeignKey("workers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("material", sa.String(120), nullable=True),
            sa.Column("quantity", sa.Numeric(14, 3), nullable=True),
            sa.Column("hours_spent", sa.Numeric(6, 2), nullable=True),
            sa.Column("cost", sa.Numeric(14, 2), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("issue_date", sa.Date(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if "ix_production_issues_project_id" not in idx:
        try:
            op.create_index("ix_production_issues_project_id", "production_issues", ["project_id"])
        except Exception:
            pass
    if "ix_production_issues_worker_id" not in idx:
        try:
            op.create_index("ix_production_issues_worker_id", "production_issues", ["worker_id"])
        except Exception:
            pass
    if "ix_production_issues_kind" not in idx:
        try:
            op.create_index("ix_production_issues_kind", "production_issues", ["kind"])
        except Exception:
            pass


def downgrade():
    for ix_name, table in [
        ("ix_production_issues_kind", "production_issues"),
        ("ix_production_issues_worker_id", "production_issues"),
        ("ix_production_issues_project_id", "production_issues"),
        ("ix_time_entries_machine_id", "time_entries"),
        ("ix_time_entries_worker_id", "time_entries"),
        ("ix_time_entries_environment_id", "time_entries"),
        ("ix_time_entries_project_id", "time_entries"),
        ("ix_project_environments_project_id", "project_environments"),
    ]:
        try:
            op.drop_index(ix_name, table_name=table)
        except Exception:
            pass
    op.execute("DROP TABLE IF EXISTS production_issues;")
    op.execute("DROP TABLE IF EXISTS time_entries;")
    op.execute("DROP TABLE IF EXISTS machines;")
    op.execute("DROP TABLE IF EXISTS workers;")
    op.execute("DROP TABLE IF EXISTS project_environments;")
