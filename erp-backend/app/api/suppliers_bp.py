"""Fornecedores: cadastro basico (compras/contas a pagar)."""
from flask import Blueprint, jsonify, request

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Supplier

bp = Blueprint("suppliers", __name__)

SUP_FIELDS = ("name", "cnpj", "contact", "phone", "email", "address", "category", "payment_terms", "avg_delivery_days")


def _validate_avg_delivery_days(value):
    if value is None or value == "":
        return None, None
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return None, "avg_delivery_days deve ser inteiro >= 0"
    if iv < 0:
        return None, "avg_delivery_days deve ser inteiro >= 0"
    return iv, None


@bp.get("/api/suppliers")
@token_required()
def list_suppliers():
    q = db.session.query(Supplier)
    category = (request.args.get("category") or "").strip()
    if category:
        q = q.filter(Supplier.category == category)
    search = (request.args.get("q") or request.args.get("search") or "").strip()
    if search:
        q = q.filter(Supplier.name.ilike(f"%{search}%"))
    rows = q.order_by(Supplier.name).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/suppliers")
@token_required()
def create_supplier():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    # valida avg_delivery_days antes de criar
    if "avg_delivery_days" in data:
        iv, err = _validate_avg_delivery_days(data.get("avg_delivery_days"))
        if err:
            return jsonify({"detail": err}), 400
    row = Supplier(name=name)
    for f in SUP_FIELDS:
        if f in data and f != "name":
            if f == "avg_delivery_days":
                iv, err = _validate_avg_delivery_days(data[f])
                if err:
                    return jsonify({"detail": err}), 400
                setattr(row, f, iv)
            else:
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
    if "avg_delivery_days" in data:
        iv, err = _validate_avg_delivery_days(data.get("avg_delivery_days"))
        if err:
            return jsonify({"detail": err}), 400
    for f in SUP_FIELDS:
        if f in data:
            if f == "avg_delivery_days":
                iv, err = _validate_avg_delivery_days(data[f])
                if err:
                    return jsonify({"detail": err}), 400
                setattr(row, f, iv)
            else:
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
