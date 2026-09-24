"""Configuracoes do sistema em chave/valor: app_settings.

Guarda o que o ADMIN configura pelo painel e que nao pode morar no codigo nem
em variavel de ambiente — hoje, a URL e a chave da Evolution API para o envio
de proposta por WhatsApp. Fica em tabela (e nao em env) porque o cliente troca
isso sem deploy; e o valor so e devolvido mascarado na leitura.
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_app_settings"
down_revision = "0024_proposals"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "app_settings" in set(insp.get_table_names()):
        return

    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    try:
        op.create_index("ix_app_settings_key", "app_settings", ["key"], unique=True)
    except Exception:
        pass


def downgrade():
    try:
        op.drop_index("ix_app_settings_key", table_name="app_settings")
    except Exception:
        pass
    op.execute("DROP TABLE IF EXISTS app_settings;")
