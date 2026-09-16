"""CRUD /api/partners - Parceiros/Arquitetos."""
from flask import Blueprint, jsonify, g
from app.extensions import db
from app.helpers import body_json
from app.auth import token_required
from app.models.models import Partner, Client

bp = Blueprint("partners", __name__)


def _enrich(partner):
    d = partner.to_dict()
    try:
        cnt = db.session.query(Client).filter_by(partner_id=partner.id).count()
    except Exception:
        cnt = 0
    d["clients_count"] = cnt
    d["projects_count"] = cnt
    return d


@bp.get("/api/partners")
@token_required()
def list_partners():
    rows = db.session.query(Partner).order_by(Partner.name).all()
    return jsonify([_enrich(p) for p in rows])


@bp.get("/api/partners/<partner_id>")
@token_required()
def get_partner(partner_id):
    p = db.session.get(Partner, partner_id)
    if not p:
        return jsonify({"detail": "Parceiro nao encontrado"}), 404
    return jsonify(_enrich(p))


@bp.post("/api/partners")
@token_required()
def create_partner():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    p = Partner(
        name=name,
        office=(data.get("office") or "").strip(),
        phone=(data.get("phone") or "").strip(),
        email=(data.get("email") or "").strip(),
        city=(data.get("city") or "").strip(),
        notes=(data.get("notes") or "").strip(),
        active=bool(data.get("active", True)) if "active" in data else True,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@bp.put("/api/partners/<partner_id>")
@token_required()
def update_partner(partner_id):
    p = db.session.get(Partner, partner_id)
    if not p:
        return jsonify({"detail": "Parceiro nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"detail": "name nao pode ser vazio"}), 400
        p.name = name
    for field in ("office", "phone", "email", "city", "notes"):
        if field in data:
            setattr(p, field, (data.get(field) or "").strip())
    if "active" in data:
        p.active = bool(data.get("active"))
    db.session.commit()
    return jsonify(p.to_dict())


@bp.delete("/api/partners/<partner_id>")
@token_required()
def delete_partner(partner_id):
    p = db.session.get(Partner, partner_id)
    if not p:
        return jsonify({"detail": "Parceiro nao encontrado"}), 404
    in_use = db.session.query(Client).filter_by(partner_id=partner_id).first()
    if in_use:
        return jsonify({"detail": "Parceiro em uso"}), 400
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})
