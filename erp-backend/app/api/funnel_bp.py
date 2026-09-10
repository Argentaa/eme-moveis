"""GET/PUT /api/funnel-columns e PUT /api/funnel-columns/<key>."""
from flask import Blueprint, jsonify, request

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import FunnelColumn

bp = Blueprint("funnel", __name__)


@bp.get("/api/funnel-columns")
@token_required()
def list_columns():
    ctype = request.args.get("type", "CRM").upper()
    rows = (
        db.session.query(FunnelColumn)
        .filter_by(type=ctype)
        .order_by(FunnelColumn.column_key)
        .all()
    )
    return jsonify([c.to_dict() for c in rows])


@bp.put("/api/funnel-columns")
@token_required()
def bulk_update():
    """Atualizacao em lote: aceita lista ou {"columns": [...]}."""
    data = request.get_json(silent=True)
    items = data if isinstance(data, list) else (data or {}).get("columns", [])
    updated = []
    for item in items:
        key = (item.get("column_key") or "").upper()
        ctype = (item.get("type") or "CRM").upper()
        if not key:
            continue
        col = db.session.query(FunnelColumn).filter_by(column_key=key, type=ctype).first()
        if not col:
            col = FunnelColumn(column_key=key, type=ctype)
            db.session.add(col)
        if "label" in item:
            col.label = item["label"]
        if "description" in item:
            col.description = item["description"]
        updated.append(col)
    db.session.commit()
    return jsonify([c.to_dict() for c in updated])


@bp.put("/api/funnel-columns/<column_key>")
@token_required()
def update_column(column_key):
    ctype = request.args.get("type", "CRM").upper()
    data = body_json()
    if data.get("type"):
        ctype = str(data["type"]).upper()
    key = (column_key or "").upper()
    col = db.session.query(FunnelColumn).filter_by(column_key=key, type=ctype).first()
    if not col:
        col = FunnelColumn(column_key=key, type=ctype)
        db.session.add(col)
    if "label" in data:
        col.label = data["label"]
    if "description" in data:
        col.description = data["description"]
    db.session.commit()
    return jsonify(col.to_dict())
