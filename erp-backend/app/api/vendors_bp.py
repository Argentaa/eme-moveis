"""Vendors: fornecedores unificados para selects de Compras/Financeiro.

Retorna todas as linhas de suppliers, marcando a origem:
- source='client' + client_id: espelho de um cliente marcado como fornecedor
  (sincronizado automaticamente no create/update de /api/clients)
- source='supplier': fornecedor independente (tabela legada)

O id retornado e SEMPRE o suppliers.id (espelho ou legado), preservando as
FKs de purchase_orders.supplier_id e financial_records.supplier_id.
"""
from flask import Blueprint, jsonify

from app.auth import token_required
from app.extensions import db
from app.models.models import Client, Supplier

bp = Blueprint("vendors", __name__)


@bp.get("/api/vendors")
@token_required()
def list_vendors():
    suppliers = db.session.query(Supplier).order_by(Supplier.name).all()
    # Clientes-fornecedores sem espelho (ex.: base antiga antes do sync):
    # incluidos como fallback com needs_mirror=true para o frontend exibir.
    mirrored_client_ids = {s.client_id for s in suppliers if s.client_id}
    orphans = (
        db.session.query(Client)
        .filter(Client.is_supplier.is_(True))
        .all()
    )
    orphans = [c for c in orphans if c.id not in mirrored_client_ids]
    rows = []
    for s in suppliers:
        d = s.to_dict()
        d["source"] = "client" if s.client_id else "supplier"
        rows.append(d)
    for c in orphans:
        rows.append({
            "id": c.id,
            "name": c.name,
            "cnpj": c.cpf_cnpj or "",
            "contact": c.contact or "",
            "phone": c.phone or "",
            "email": c.email or "",
            "category": c.category or "",
            "avg_delivery_days": c.avg_delivery_days,
            "source": "client",
            "client_id": c.id,
            "is_supplier": True,
            "needs_mirror": True,
        })
    rows.sort(key=lambda r: (r["name"] or "").lower())
    return jsonify(rows)
