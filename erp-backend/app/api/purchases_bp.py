"""CRUD /api/purchases + recebimento que baixa no estoque."""
from datetime import date, datetime, timezone

from flask import Blueprint, g, jsonify, request

from app.auth import token_required
from app.extensions import db
from app.helpers import body_json, iso, num, parse_date
from app.models.models import (
    PurchaseItem, PurchaseOrder, PurchaseQuotation, PurchaseQuotationItem,
    StockItem, StockMovement, Supplier,
)

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
        carrier=(data.get("carrier") or "").strip() or None,
        tracking=(data.get("tracking") or "").strip() or None,
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

    if "carrier" in data:
        order.carrier = (data.get("carrier") or "").strip() or None

    if "tracking" in data:
        order.tracking = (data.get("tracking") or "").strip() or None

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


# ── COTACOES ──────────────────────────────────────────────────────
def _aplicar_itens_cotacao(quotation, itens):
    """Recria os precos da cotacao.

    Recria em vez de casar linha a linha: o comparativo manda a lista inteira a
    cada gravacao, e casar por id so criaria chance de sobrar preco orfao
    apontando para um item que ja saiu do pedido.
    """
    for antigo in list(quotation.items):
        db.session.delete(antigo)
    quotation.items = []
    for it in itens or []:
        if not isinstance(it, dict):
            continue
        pid = it.get("purchase_item_id")
        if not pid:
            continue
        item = db.session.get(PurchaseItem, pid)
        if not item or item.order_id != quotation.order_id:
            continue  # item de outro pedido nao entra nesta cotacao
        quotation.items.append(PurchaseQuotationItem(
            purchase_item_id=pid,
            unit_price=it.get("unit_price") or 0,
        ))


def _parse_delivery_days(valor):
    """(dias, erro). Dias negativos nao existem: -1 viraria prazo no passado."""
    if valor in (None, ""):
        return None, None
    try:
        dias = int(valor)
    except (TypeError, ValueError):
        return None, "delivery_days deve ser um numero de dias"
    if dias < 0:
        return None, "delivery_days nao pode ser negativo"
    return dias, None


@bp.get("/api/purchases/<order_id>/quotations")
@token_required()
def list_quotations(order_id):
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404
    return jsonify([q.to_dict() for q in order.quotations])


@bp.post("/api/purchases/<order_id>/quotations")
@token_required()
def create_quotation(order_id):
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404

    data = body_json()
    supplier_id = data.get("supplier_id")
    if supplier_id not in (None, ""):
        if not db.session.get(Supplier, supplier_id):
            return jsonify({"detail": "Fornecedor nao encontrado"}), 400
    else:
        supplier_id = None

    dias, err = _parse_delivery_days(data.get("delivery_days"))
    if err:
        return jsonify({"detail": err}), 400

    q = PurchaseQuotation(
        order_id=order.id,
        supplier_id=supplier_id,
        delivery_days=dias,
        payment_terms=(data.get("payment_terms") or "").strip() or None,
        notes=(data.get("notes") or "").strip() or None,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(q)
    db.session.flush()
    _aplicar_itens_cotacao(q, data.get("items"))
    db.session.commit()
    return jsonify(q.to_dict()), 201


@bp.put("/api/quotations/<quotation_id>")
@token_required()
def update_quotation(quotation_id):
    q = db.session.get(PurchaseQuotation, quotation_id)
    if not q:
        return jsonify({"detail": "Cotacao nao encontrada"}), 404
    data = body_json()

    if "supplier_id" in data:
        sid = data.get("supplier_id")
        if sid in (None, ""):
            q.supplier_id = None
        else:
            if not db.session.get(Supplier, sid):
                return jsonify({"detail": "Fornecedor nao encontrado"}), 400
            q.supplier_id = sid

    if "delivery_days" in data:
        dias, err = _parse_delivery_days(data.get("delivery_days"))
        if err:
            return jsonify({"detail": err}), 400
        q.delivery_days = dias

    if "payment_terms" in data:
        q.payment_terms = (data.get("payment_terms") or "").strip() or None
    if "notes" in data:
        q.notes = (data.get("notes") or "").strip() or None
    if "items" in data:
        _aplicar_itens_cotacao(q, data.get("items"))

    db.session.commit()
    return jsonify(q.to_dict())


@bp.delete("/api/quotations/<quotation_id>")
@token_required()
def delete_quotation(quotation_id):
    q = db.session.get(PurchaseQuotation, quotation_id)
    if not q:
        return jsonify({"detail": "Cotacao nao encontrada"}), 404
    db.session.delete(q)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/purchases/<order_id>/quotations/<quotation_id>/approve")
@token_required()
def approve_quotation(order_id, quotation_id):
    """Marca a cotacao vencedora e leva os precos dela para o pedido.

    A vencedora e UNICA — as outras sao desmarcadas. Sem isso a economia
    medida (saving_real) contaria o mesmo item duas vezes. O pedido sai de
    SOLICITADA/COTANDO para APROVADA, e o fornecedor passa a ser o da cotacao.
    """
    order = db.session.get(PurchaseOrder, order_id)
    if not order:
        return jsonify({"detail": "Compra nao encontrada"}), 404
    q = db.session.get(PurchaseQuotation, quotation_id)
    if not q or q.order_id != order.id:
        return jsonify({"detail": "Cotacao nao encontrada nesta compra"}), 404
    if order.status == "RECEBIDA":
        return jsonify({"detail": "Compra ja recebida"}), 400

    for outra in order.quotations:
        outra.is_winner = (outra.id == q.id)

    for qi in q.items:
        item = db.session.get(PurchaseItem, qi.purchase_item_id)
        if item and item.order_id == order.id:
            item.unit_price = qi.unit_price

    if q.supplier_id:
        order.supplier_id = q.supplier_id
    if order.status in ("SOLICITADA", "COTANDO"):
        order.status = "APROVADA"

    db.session.commit()
    return jsonify(order.to_dict())
