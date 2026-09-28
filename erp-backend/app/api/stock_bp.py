"""CRUD /api/stock, /movements e /categories."""
from datetime import date

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.helpers import body_json, iso, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import Category, StockItem, StockLoss, StockMovement

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


# ── Perdas e avarias ──────────────────────────────────────────────
#
# Uma perda NAO e um simples ajuste de quantidade: ela precisa dizer o motivo e
# quanto custou, senao o prejuizo nao tem como ser somado depois. Por isso o
# registro vive em `stock_losses` E decrementa o estoque, na mesma transacao.

LOSS_KINDS = ("PERDA", "AVARIA")


def _loss_filters(query):
    kind = (request.args.get("kind") or "").strip().upper()
    if kind in LOSS_KINDS:
        query = query.filter(StockLoss.kind == kind)
    item_id = request.args.get("stock_item_id") or None
    if item_id:
        query = query.filter(StockLoss.stock_item_id == item_id)
    df = parse_date(request.args.get("date_from"))
    dt = parse_date(request.args.get("date_to"))
    if df:
        query = query.filter(StockLoss.loss_date >= df)
    if dt:
        query = query.filter(StockLoss.loss_date <= dt)
    return query


@bp.get("/api/stock/losses")
@token_required()
def list_losses():
    rows = _loss_filters(db.session.query(StockLoss)).order_by(
        StockLoss.loss_date.desc(), StockLoss.created_at.desc()
    ).all()
    return jsonify([l.to_dict() for l in rows])


@bp.post("/api/stock/losses")
@token_required()
def create_loss():
    data = body_json()
    item = db.session.get(StockItem, data.get("stock_item_id") or "")
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404

    kind = str(data.get("kind") or "").strip().upper()
    if kind not in LOSS_KINDS:
        return jsonify({"detail": "kind deve ser PERDA ou AVARIA"}), 400

    try:
        qty = float(data.get("quantity") or 0)
    except (TypeError, ValueError):
        return jsonify({"detail": "quantity invalida"}), 400
    if qty <= 0:
        return jsonify({"detail": "quantity deve ser maior que zero"}), 400

    # Nao deixar o estoque ficar negativo: uma perda maior que o saldo quer dizer
    # que o saldo ja estava errado. Recusar forca corrigir o estoque primeiro, em
    # vez de gravar um numero impossivel que ninguem vai entender depois.
    saldo = float(item.quantity or 0)
    if qty > saldo:
        return jsonify({
            "detail": f"quantidade maior que o estoque atual ({saldo:g})"
        }), 400

    # Custo: usa o que foi informado; sem informar, vale o preco cadastrado do
    # item vezes a quantidade perdida — que e o valor do prejuizo por definicao.
    raw_cost = data.get("cost")
    if raw_cost in (None, ""):
        cost = round(float(item.price or 0) * qty, 2)
    else:
        try:
            cost = float(raw_cost)
        except (TypeError, ValueError):
            return jsonify({"detail": "cost invalido"}), 400
        if cost < 0:
            return jsonify({"detail": "cost nao pode ser negativo"}), 400

    loss = StockLoss(
        stock_item_id=item.id,
        quantity=qty,
        kind=kind,
        reason=data.get("reason") or "",
        cost=cost,
        loss_date=parse_date(data.get("loss_date")) or date.today(),
        created_by=g.current_user.username if hasattr(g, "current_user") else "",
    )
    item.quantity = saldo - qty
    mov = StockMovement(
        item_id=item.id,
        type="PERDA",
        quantity=qty,
        reason=f"{kind}: {data.get('reason') or ''}".strip(": ").strip(),
        created_by=loss.created_by,
    )
    db.session.add(loss)
    db.session.add(mov)
    db.session.commit()
    return jsonify(loss.to_dict()), 201


@bp.get("/api/stock/losses/summary")
@token_required()
def losses_summary():
    """Prejuizo do periodo: total, por tipo e por motivo.

    O motivo e texto livre, entao o agrupamento e por texto exato — motivo
    escrito de duas formas conta como dois. Ordenado por custo, que e o que
    interessa para decidir onde agir.
    """
    rows = _loss_filters(db.session.query(StockLoss)).all()

    def _bloco(chave, valor):
        return {
            "key": valor,
            "count": len(chave),
            "quantity": round(sum(float(l.quantity or 0) for l in chave), 3),
            "cost": round(sum(float(l.cost or 0) for l in chave), 2),
        }

    por_tipo = {k: [] for k in LOSS_KINDS}
    por_motivo = {}
    for l in rows:
        por_tipo.setdefault(l.kind, []).append(l)
        por_motivo.setdefault((l.reason or "(sem motivo)").strip() or "(sem motivo)", []).append(l)

    by_kind = [_bloco(por_tipo.get(k, []), k) for k in LOSS_KINDS]
    by_reason = sorted(
        (_bloco(v, k) for k, v in por_motivo.items()),
        key=lambda b: b["cost"], reverse=True,
    )

    return jsonify({
        "count": len(rows),
        "total_quantity": round(sum(float(l.quantity or 0) for l in rows), 3),
        "total_cost": round(sum(float(l.cost or 0) for l in rows), 2),
        "by_kind": by_kind,
        "by_reason": by_reason,
        "date_from": iso(parse_date(request.args.get("date_from"))),
        "date_to": iso(parse_date(request.args.get("date_to"))),
    })
