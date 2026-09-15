"""CRUD /api/purchases + recebimento que baixa no estoque."""
from datetime import date, datetime, timezone

from flask import Blueprint, g, jsonify, request

from app.auth import token_required
from app.extensions import db
from app.helpers import body_json, iso, num, parse_date
from app.models.models import PurchaseItem, PurchaseOrder, StockItem, StockMovement, Supplier

bp = Blueprint("purchases", __name__)

VALID_STATUSES = ("SOLICITADA", "COTANDO", "APROVADA", "COMPRADA", "RECEBIDA", "CANCELADA")


def _next_purchase_number():
    year = date.today().year
    prefix = f"PC-{year}-"
    # busca MAX number com like prefix
    row = (
        db.session.query(PurchaseOrder)
        .filter(PurchaseOrder.number.like(f"{prefix}%"))
        .order_by(PurchaseOrder.number.desc())
        .first()
    )
    if row and row.number:
        try:
            suffix = row.number.split("-")[-1]
            n = int(suffix)
        except Exception:
            n = 0
        nxt = n + 1
    else:
        nxt = 1
    return f"{prefix}{nxt:04d}"


def _validate_items(items):
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"detail": "items e obrigatorio e deve conter ao menos um item"}), 400
    for it in items:
        if not isinstance(it, dict):
            return jsonify({"detail": "items deve ser lista de objetos"}), 400
        material = it.get("material_name")
        if not isinstance(material, str) or not material.strip():
            return jsonify({"detail": "material_name e obrigatorio"}), 400
        # quantity
        qty_raw = it.get("quantity")
        try:
            qty = float(qty_raw) if qty_raw is not None else 0
        except (TypeError, ValueError):
            return jsonify({"detail": "quantity invalida"}), 400
        if qty <= 0:
            return jsonify({"detail": "quantity deve ser maior que zero"}), 400
        # unit_price
        up_raw = it.get("unit_price")
        if up_raw is None:
            up_raw = 0
        try:
            up = float(up_raw)
        except (TypeError, ValueError):
            return jsonify({"detail": "unit_price invalido"}), 400
        if up < 0:
            return jsonify({"detail": "unit_price deve ser maior ou igual a zero"}), 400
        # stock_item_id
        sid = it.get("stock_item_id")
        if sid not in (None, ""):
            if not db.session.get(StockItem, sid):
                return jsonify({"detail": "Item de estoque nao encontrado"}), 404
    return None


def _apply_items(order, items):
    # limpa order.items e recria PurchaseItem com position=i
    # delete existing orphans
    for old in list(order.items):
        db.session.delete(old)
    db.session.flush()
    for i, it in enumerate(items):
        material_name = it.get("material_name").strip() if isinstance(it.get("material_name"), str) else it.get("material_name")
        qty = float(it.get("quantity"))
        up = float(it.get("unit_price")) if it.get("unit_price") is not None else 0
        sid = it.get("stock_item_id")
        if sid == "":
            sid = None
        pi = PurchaseItem(
            order_id=order.id,
            stock_item_id=sid,
            material_name=material_name,
            quantity=qty,
            unit_price=up,
            position=i,
            received_qty=0,
        )
        db.session.add(pi)
    # ensure relationship reflects flush; no need to append
    db.session.flush()


# ── LIST ──────────────────────────────────────────────────────────
@bp.get("/api/purchases")
@token_required()
def list_purchases():
    q = db.session.query(PurchaseOrder)
    status = request.args.get("status")
    supplier_id = request.args.get("supplier_id")
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    rows = q.order_by(PurchaseOrder.created_at.desc()).all()
    return jsonify([r.to_dict() for r in rows])


# ── CREATE ────────────────────────────────────────────────────────
@bp.post("/api/purchases")
@token_required()
def create_purchase():
    data = body_json()

    # supplier validation
    supplier_id = data.get("supplier_id")
    if supplier_id not in (None, ""):
        if not db.session.get(Supplier, supplier_id):
            return jsonify({"detail": "Fornecedor nao encontrado"}), 400
    else:
        supplier_id = None

    # items validation
    items = data.get("items")
    err = _validate_items(items)
    if err:
        return err

    # status
    raw_status = data.get("status")
    if raw_status is None or (isinstance(raw_status, str) and not raw_status.strip()):
        status = "SOLICITADA"
    else:
        status = str(raw_status).strip().upper()
        if status not in VALID_STATUSES:
            return jsonify({"detail": "status invalido"}), 400
    if status == "RECEBIDA":
        return jsonify({"detail": "Nao e permitido criar compra ja recebida"}), 400

    # request_date
    try:
        rd = parse_date(data.get("request_date")) if data.get("request_date") not in (None, "") else None
    except Exception:
        return jsonify({"detail": "request_date invalida"}), 400
    if not rd:
        rd = date.today()

    # expected_date
    try:
        ed = parse_date(data.get("expected_date")) if data.get("expected_date") not in (None, "") else None
    except Exception:
        return jsonify({"detail": "expected_date invalida"}), 400

    number = _next_purchase_number()
    order = PurchaseOrder(
        number=number,
        status=status,
        supplier_id=supplier_id,
        request_date=rd,
        expected_date=ed,
        notes=data.get("notes") or "",
        created_by=g.current_user.username if hasattr(g, "current_user") else "",
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(order)
    db.session.flush()
    _apply_items(order, items)
    db.session.commit()
    return jsonify(order.to_dict()), 201


# ── GET ONE ───────────────────────────────────────────────────────
@bp.get("/api/purchases/<order_id>")
@token_required()
def get_purchase(order_id):
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404
    return jsonify(order.to_dict())


# ── UPDATE ────────────────────────────────────────────────────────
@bp.put("/api/purchases/<order_id>")
@token_required()
def update_purchase(order_id):
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404
    if order.status == "RECEBIDA":
        return jsonify({"detail": "Compra ja recebida"}), 400

    data = body_json()

    # valida items se houver no payload
    if "items" in data:
        err = _validate_items(data.get("items"))
        if err:
            return err

    # supplier_id
    if "supplier_id" in data:
        sid = data.get("supplier_id")
        if sid in (None, ""):
            order.supplier_id = None
        else:
            if not db.session.get(Supplier, sid):
                return jsonify({"detail": "Fornecedor nao encontrado"}), 400
            order.supplier_id = sid

    # request_date
    if "request_date" in data:
        try:
            rd = parse_date(data.get("request_date")) if data.get("request_date") not in (None, "") else None
        except Exception:
            return jsonify({"detail": "request_date invalida"}), 400
        if rd:
            order.request_date = rd

    # expected_date
    if "expected_date" in data:
        try:
            ed = parse_date(data.get("expected_date")) if data.get("expected_date") not in (None, "") else None
        except Exception:
            return jsonify({"detail": "expected_date invalida"}), 400
        order.expected_date = ed

    if "notes" in data:
        order.notes = data.get("notes") or ""

    if "status" in data:
        st = str(data.get("status")).strip().upper() if isinstance(data.get("status"), str) else ""
        if st:
            if st not in VALID_STATUSES:
                return jsonify({"detail": "status invalido"}), 400
            order.status = st

    if "items" in data:
        _apply_items(order, data.get("items"))

    db.session.commit()
    return jsonify(order.to_dict())


# ── DELETE ────────────────────────────────────────────────────────
@bp.delete("/api/purchases/<order_id>")
@token_required()
def delete_purchase(order_id):
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404
    if order.status == "RECEBIDA":
        return jsonify({"detail": "Compra ja recebida"}), 400
    db.session.delete(order)
    db.session.commit()
    return "", 204


# ── RECEIVE ───────────────────────────────────────────────────────
@bp.post("/api/purchases/<order_id>/receive")
@token_required()
def receive_purchase(order_id):
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404
    if order.status == "RECEBIDA":
        return jsonify({"detail": "Compra ja recebida"}), 400
    if order.status == "CANCELADA":
        return jsonify({"detail": "Compra cancelada"}), 400

    for item in order.items:
        if item.stock_item_id:
            stock = db.session.get(StockItem, item.stock_item_id)
            if stock:
                qty = float(item.quantity or 0)
                stock.quantity = float(stock.quantity or 0) + qty
                mov = StockMovement(
                    item_id=stock.id,
                    type="ENTRADA",
                    quantity=qty,
                    reason=f"Recebimento {order.number}",
                    created_by=g.current_user.username if hasattr(g, "current_user") else "",
                )
                db.session.add(mov)
        item.received_qty = item.quantity

    order.status = "RECEBIDA"
    order.received_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(order.to_dict())
