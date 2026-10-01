"""Catalogo de produtos/servicos pre-cadastrados."""
from flask import Blueprint, jsonify, request

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Product

bp = Blueprint("products", __name__)


@bp.get("/api/products")
@token_required()
def list_products():
    q = db.session.query(Product)
    if request.args.get("all") != "1":
        q = q.filter_by(active=True)
    return jsonify([p.to_dict() for p in q.order_by(Product.name).all()])


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


@bp.put("/api/products/<product_id>")
@token_required()
def update_product(product_id):
    """Edicao do catalogo (aba Produtos/Moveis do Comercial)."""
    row = db.session.get(Product, product_id)
    if not row:
        return jsonify({"detail": "Produto nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"detail": "name nao pode ser vazio"}), 400
        dup = db.session.query(Product).filter(Product.name == name, Product.id != row.id).first()
        if dup:
            return jsonify({"detail": "Ja existe produto com este nome"}), 400
        row.name = name
    if "description" in data:
        row.description = (data.get("description") or "")
    if "default_price" in data:
        row.default_price = data.get("default_price")
    if "unit" in data and data.get("unit") is not None:
        row.unit = (data.get("unit") or "un")
    if "active" in data:
        row.active = bool(data.get("active"))
    db.session.commit()
    return jsonify(row.to_dict())
