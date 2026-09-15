"""Fornecedores: cadastro basico (compras/contas a pagar)."""
from flask import Blueprint, jsonify

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Supplier

bp = Blueprint("suppliers", __name__)

SUP_FIELDS = ("name", "cnpj", "contact", "phone", "email")


@bp.get("/api/suppliers")
@token_required()
def list_suppliers():
    rows = db.session.query(Supplier).order_by(Supplier.name).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/suppliers")
@token_required()
def create_supplier():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    row = Supplier(name=name)
    for f in SUP_FIELDS:
        if f in data and f != "name":
            v = data[f]
            setattr(row, f, v.strip() if isinstance(v, str) else v)
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@bp.put("/api/suppliers/<supplier_id>")
@token_required()
def update_supplier(supplier_id):
    row = db.session.get(Supplier, supplier_id)
    if not row:
        return jsonify({"detail": "Fornecedor nao encontrado"}), 404
    data = body_json()
    if "name" in data and not (data.get("name") or "").strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    for f in SUP_FIELDS:
        if f in data:
            v = data[f]
            setattr(row, f, v.strip() if isinstance(v, str) else v)
    db.session.commit()
    return jsonify(row.to_dict())


@bp.delete("/api/suppliers/<supplier_id>")
@token_required()
def delete_supplier(supplier_id):
    row = db.session.get(Supplier, supplier_id)
    if not row:
        return jsonify({"detail": "Fornecedor nao encontrado"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})