"""GET/POST/DELETE /api/lead-sources e /api/campaigns (opcoes personalizaveis)."""
from flask import Blueprint, jsonify

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import LeadSource, Campaign

bp = Blueprint("lead_options", __name__)


def _create_or_reactivate(model, name):
    existing = db.session.query(model).filter_by(name=name).first()
    if existing:
        existing.active = True
        db.session.commit()
        return existing, 200
    row = model(name=name)
    db.session.add(row)
    db.session.commit()
    return row, 201


@bp.get("/api/lead-sources")
@token_required()
def list_sources():
    rows = db.session.query(LeadSource).filter_by(active=True).order_by(LeadSource.name).all()
    return jsonify([s.to_dict() for s in rows])


@bp.post("/api/lead-sources")
@token_required()
def create_source():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    row, status = _create_or_reactivate(LeadSource, name)
    return jsonify(row.to_dict()), status


@bp.delete("/api/lead-sources/<source_id>")
@token_required()
def delete_source(source_id):
    src = db.session.get(LeadSource, source_id)
    if not src:
        return jsonify({"detail": "Fonte nao encontrada"}), 404
    src.active = False  # soft delete: clientes mantem o texto
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/campaigns")
@token_required()
def list_campaigns():
    rows = db.session.query(Campaign).filter_by(active=True).order_by(Campaign.name).all()
    return jsonify([c.to_dict() for c in rows])


@bp.post("/api/campaigns")
@token_required()
def create_campaign():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    row, status = _create_or_reactivate(Campaign, name)
    return jsonify(row.to_dict()), status


@bp.delete("/api/campaigns/<campaign_id>")
@token_required()
def delete_campaign(campaign_id):
    camp = db.session.get(Campaign, campaign_id)
    if not camp:
        return jsonify({"detail": "Campanha nao encontrada"}), 404
    camp.active = False
    db.session.commit()
    return jsonify({"ok": True})
