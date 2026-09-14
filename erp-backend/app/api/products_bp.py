"""Catalogo de produtos/servicos pre-cadastrados."""
from flask import Blueprint, jsonify

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Product

bp = Blueprint("products", __name__)


@bp.get("/api/products")
@token_required()
def list_products():
    rows = db.session.query(Product).filter_by(active=True).order_by(Product.name).all()
    return jsonify([p.to_dict() for p in rows])


@bp.post("/api/products")
@token_required()
def create_product():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    existing = db.session.query(Product).filter_by(name=name).first()
    if existing:
        existing.active = True
        if data.get("default_price") is not None:
            existing.default_price = data["default_price"]
        db.session.commit()
        return jsonify(existing.to_dict()), 200
    row = Product(name=name, description=(data.get("description") or ""),
                  default_price=data.get("default_price"), unit=data.get("unit") or "un")
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@bp.delete("/api/products/<product_id>")
@token_required()
def delete_product(product_id):
    row = db.session.get(Product, product_id)
    if not row:
        return jsonify({"detail": "Produto nao encontrado"}), 404
    row.active = False  # soft delete: itens vinculados mantem o snapshot do nome
    db.session.commit()
    return jsonify({"ok": True})