"""CRUD /api/stock, /movements e /categories."""
from flask import Blueprint, g, jsonify
from sqlalchemy.exc import IntegrityError

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Category, StockItem, StockMovement

bp = Blueprint("stock", __name__)

ITEM_FIELDS = (
    "name", "sku", "category_id", "quantity", "min_quantity", "unit", "price", "supplier",
)


@bp.get("/api/stock/movements/history")
@token_required()
def movements_history():
    rows = db.session.query(StockMovement).order_by(StockMovement.date.desc()).all()
    return jsonify([m.to_dict() for m in rows])


@bp.post("/api/stock/movements")
@token_required()
def create_movement():
    data = body_json()
    item = db.session.get(StockItem, data.get("item_id") or "")
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404
    if data.get("type") not in ("ENTRADA", "SAIDA"):
        return jsonify({"detail": "type deve ser ENTRADA ou SAIDA"}), 400
    try:
        qty = float(data.get("quantity") or 0)
    except (TypeError, ValueError):
        return jsonify({"detail": "quantity invalida"}), 400
    if qty <= 0:
        return jsonify({"detail": "quantity deve ser maior que zero"}), 400
    if data["type"] == "SAIDA":
        item.quantity = float(item.quantity or 0) - qty
    else:
        item.quantity = float(item.quantity or 0) + qty
    mov = StockMovement(
        item_id=item.id,
        type=data["type"],
        quantity=qty,
        reason=data.get("reason") or "",
        created_by=g.current_user.username if hasattr(g, "current_user") else "",
    )
    db.session.add(mov)
    db.session.commit()
    return jsonify(mov.to_dict()), 201


@bp.get("/api/stock/categories/all")
@token_required()
def list_categories():
    from flask import request

    ctype = request.args.get("category_type")
    q = db.session.query(Category)
    if ctype:
        q = q.filter_by(category_type=ctype)
    return jsonify([c.to_dict() for c in q.order_by(Category.name).all()])


@bp.post("/api/stock/categories")
@token_required()
def create_category():
    data = body_json()
    if not (data.get("name") or "").strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    cat = Category(
        name=data["name"].strip(),
        description=data.get("description"),
        category_type=data.get("category_type") or "STOCK",
    )
    db.session.add(cat)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "Categoria ja cadastrada para este tipo"}), 400
    return jsonify(cat.to_dict()), 201


@bp.put("/api/stock/categories/<category_id>")
@token_required()
def update_category(category_id):
    cat = db.session.get(Category, category_id)
    if not cat:
        return jsonify({"detail": "Categoria nao encontrada"}), 404
    data = body_json()
    if "name" in data:
        cat.name = data["name"]
    if "description" in data:
        cat.description = data["description"]
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "Categoria ja cadastrada para este tipo"}), 400
    return jsonify(cat.to_dict())


@bp.delete("/api/stock/categories/<category_id>")
@token_required()
def delete_category(category_id):
    cat = db.session.get(Category, category_id)
    if not cat:
        return jsonify({"detail": "Categoria nao encontrada"}), 404
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/stock")
@token_required()
def list_items():
    rows = db.session.query(StockItem).order_by(StockItem.name).all()
    return jsonify([i.to_dict() for i in rows])


@bp.post("/api/stock")
@token_required()
def create_item():
    data = body_json()
    if not (data.get("name") or "").strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    if not (data.get("sku") or "").strip():
        return jsonify({"detail": "sku e obrigatorio"}), 400
    if not data.get("category_id"):
        return jsonify({"detail": "category_id e obrigatorio"}), 400
    if not db.session.get(Category, data["category_id"]):
        return jsonify({"detail": "Categoria nao encontrada"}), 400
    item = StockItem()
    for f in ITEM_FIELDS:
        if f in data:
            setattr(item, f, data[f])
    db.session.add(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "sku ja cadastrado"}), 400
    return jsonify(item.to_dict()), 201


@bp.get("/api/stock/<item_id>")
@token_required()
def get_item(item_id):
    item = db.session.get(StockItem, item_id)
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404
    return jsonify(item.to_dict())


@bp.put("/api/stock/<item_id>")
@token_required()
def update_item(item_id):
    item = db.session.get(StockItem, item_id)
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404
    data = body_json()
    if "category_id" in data and data["category_id"] and not db.session.get(Category, data["category_id"]):
        return jsonify({"detail": "Categoria nao encontrada"}), 400
    for f in ITEM_FIELDS:
        if f in data:
            setattr(item, f, data[f])
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "sku ja cadastrado"}), 400
    return jsonify(item.to_dict())


@bp.delete("/api/stock/<item_id>")
@token_required()
def delete_item(item_id):
    item = db.session.get(StockItem, item_id)
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})
