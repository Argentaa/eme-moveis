"""Regras de comissao: commission_rules.

A comissao e uma REGRA (percentual + vigencia) aplicada sobre as vendas
fechadas do periodo — nao um valor congelado. Assim, mudar o percentual de um
vendedor no mes que vem nao reescreve o que ja foi pago nos meses anteriores.

A regra vale para vendedor OU parceiro (arquiteto indicador): exatamente um dos
dois e preenchido. Vigencia nula = regra sempre valida.

Numeracao: o plano chamava esta de 0022; o encadeamento real vem de
0025_app_settings, entao ela e a 0026.
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_commission_rules"
down_revision = "0025_app_settings"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "commission_rules" in set(insp.get_table_names()):
        return

    op.create_table(
        "commission_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("seller_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("partner_id", sa.String(36),
                  sa.ForeignKey("partners.id", ondelete="SET NULL"), nullable=True),
        sa.Column("percent", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for name, col in (("ix_commission_rules_seller_id", "seller_id"),
                      ("ix_commission_rules_partner_id", "partner_id")):
        try:
            op.create_index(name, "commission_rules", [col])
        except Exception:
            pass


def downgrade():
    for name in ("ix_commission_rules_partner_id", "ix_commission_rules_seller_id"):
        try:
            op.drop_index(name, table_name="commission_rules")
        except Exception:
            pass
    op.execute("DROP TABLE IF EXISTS commission_rules;")
