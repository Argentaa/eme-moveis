"""CRUD /api/clients."""
from flask import Blueprint, jsonify
from sqlalchemy.exc import IntegrityError

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Client

bp = Blueprint("clients", __name__)

CLIENT_FIELDS = (
    "name", "email", "phone", "cpf_cnpj", "address",
    "funnel_status", "lost_reason", "estimated_value", "lead_source",
)


@bp.get("/api/clients")
@token_required()
def list_clients():
    clients = db.session.query(Client).order_by(Client.created_at.desc()).all()
    return jsonify([c.to_dict() for c in clients])


@bp.post("/api/clients")
@token_required()
def create_client():
    data = body_json()
    if not (data.get("name") or "").strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    client = Client()
    for f in CLIENT_FIELDS:
        if f in data:
            setattr(client, f, data[f] if data[f] != "" or f in ("email", "phone", "address") else None)
    if not client.cpf_cnpj:
        client.cpf_cnpj = None
    if not client.funnel_status:
        client.funnel_status = "PROSPECCAO"
    db.session.add(client)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "cpf_cnpj ja cadastrado"}), 400
    return jsonify(client.to_dict()), 201


@bp.get("/api/clients/<client_id>")
@token_required()
def get_client(client_id):
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    return jsonify(client.to_dict())


@bp.put("/api/clients/<client_id>")
@token_required()
def update_client(client_id):
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    data = body_json()
    for f in CLIENT_FIELDS:
        if f in data:
            setattr(client, f, data[f])
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "cpf_cnpj ja cadastrado"}), 400
    return jsonify(client.to_dict())


@bp.delete("/api/clients/<client_id>")
@token_required()
def delete_client(client_id):
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    db.session.delete(client)
    db.session.commit()
    return jsonify({"ok": True})
