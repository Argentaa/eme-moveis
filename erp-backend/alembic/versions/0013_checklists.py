"""Checklists por etapa do projeto (checklist_items)."""

from alembic import op
import sqlalchemy as sa

revision = "0013_checklists"
down_revision = "0012_project_attachments"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    # coletar indices existentes para idempotencia
    idx = set()
    for tname in tables:
        try:
            for i in insp.get_indexes(tname):
                if i.get("name"):
                    idx.add(i["name"])
        except Exception:
            pass
    if "checklist_items" not in tables:
        op.create_table(
            "checklist_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("step_id", sa.String(60), nullable=False),
            sa.Column("label", sa.String(200), nullable=False),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("assigned_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True, server_default=""),
            sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        # atualizar sets apos criacao para criar indices abaixo
        tables.add("checklist_items")
        # recarregar idx para nova tabela (vazia)
    if "ix_checklist_items_project_id" not in idx:
        try:
            op.create_index("ix_checklist_items_project_id", "checklist_items", ["project_id"])
        except Exception:
            pass
    if "ix_checklist_items_assigned_user_id" not in idx:
        try:
            op.create_index("ix_checklist_items_assigned_user_id", "checklist_items", ["assigned_user_id"])
        except Exception:
            pass


def downgrade():
    try:
        op.drop_index("ix_checklist_items_assigned_user_id", table_name="checklist_items")
    except Exception:
        pass
    try:
        op.drop_index("ix_checklist_items_project_id", table_name="checklist_items")
    except Exception:
        pass
    op.drop_table("checklist_items")
