"""CRUD /api/clients."""
from flask import Blueprint, g, jsonify
from sqlalchemy.exc import IntegrityError

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    Attachment,
    CalendarEvent,
    Campaign,
    Client,
    Interaction,
    LeadSource,
    NegotiationItem,
    Project,
)

bp = Blueprint("clients", __name__)

CLIENT_FIELDS = (
    "name", "email", "phone", "cpf_cnpj", "address",
    "funnel_status", "lost_reason", "estimated_value", "lead_source", "campaign",
)

INTERACTION_TYPES = ("CONVERSA", "PROPOSTA", "ORCAMENTO", "OBSERVACAO")


def _fmt_log(value):
    """Formata valores opcionais/None para os logs de interacao."""
    if value is None or value == "":
        return "não informado"
    return str(value)


def _upsert_option(model, name):
    """Insere uma opcao (fonte/campanha) caso ainda nao exista."""
    name = (name or "").strip()
    if not name:
        return
    existing = db.session.query(model).filter_by(name=name).first()
    if not existing:
        db.session.add(model(name=name))


def _log_interaction(client_id, itype, content):
    """Registra interacao automatica de sistema para o cliente."""
    db.session.add(Interaction(client_id=client_id, type=itype, content=content, automatic=True))


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
    _upsert_option(LeadSource, client.lead_source)
    _upsert_option(Campaign, client.campaign)
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


@bp.get("/api/clients/<client_id>/detail")
@token_required()
def get_client_detail(client_id):
    """Detalhe agregado do cliente: projetos, eventos, interacoes, anexos e itens."""
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    projects = (db.session.query(Project).filter_by(client_id=client_id)
                .order_by(Project.created_at).all())
    events = (db.session.query(CalendarEvent).filter_by(client_id=client_id)
              .order_by(CalendarEvent.start_date, CalendarEvent.start_time).all())
    interactions = (db.session.query(Interaction).filter_by(client_id=client_id)
                    .order_by(Interaction.created_at.desc()).all())
    attachments = (db.session.query(Attachment).filter_by(client_id=client_id)
                   .order_by(Attachment.created_at.desc()).all())
    items = (db.session.query(NegotiationItem).filter_by(client_id=client_id)
             .order_by(NegotiationItem.created_at).all())
    return jsonify({
        "client": client.to_dict(),
        "projects": [p.to_dict() for p in projects],
        "events": [e.to_dict() for e in events],
        "interactions": [i.to_dict() for i in interactions],
        "attachments": [a.to_dict() for a in attachments],
        "items": [it.to_dict() for it in items],
    })


@bp.get("/api/clients/<client_id>/interactions")
@token_required()
def list_interactions(client_id):
    """Lista as interacoes (historico) de um cliente, da mais recente a mais antiga."""
    rows = (db.session.query(Interaction).filter_by(client_id=client_id)
            .order_by(Interaction.created_at.desc()).all())
    return jsonify([i.to_dict() for i in rows])


@bp.post("/api/clients/<client_id>/interactions")
@token_required()
def create_interaction(client_id):
    """Cria uma interacao manual no historico do cliente."""
    data = body_json()
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"detail": "content e obrigatorio"}), 400
    itype = (data.get("type") or "OBSERVACAO").upper()
    if itype not in INTERACTION_TYPES:
        itype = "OBSERVACAO"
    row = Interaction(client_id=client_id, type=itype, content=content,
                      created_by=g.current_user.username if hasattr(g, "current_user") else "",
                      automatic=False)
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@bp.delete("/api/interactions/<interaction_id>")
@token_required()
def delete_interaction(interaction_id):
    """Remove uma interacao do historico."""
    row = db.session.get(Interaction, interaction_id)
    if not row:
        return jsonify({"detail": "Interacao nao encontrada"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})


@bp.put("/api/clients/<client_id>")
@token_required()
def update_client(client_id):
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    data = body_json()
    old_funnel = client.funnel_status
    old_value = client.estimated_value
    old_source = client.lead_source
    old_campaign = client.campaign
    for f in CLIENT_FIELDS:
        if f in data:
            setattr(client, f, data[f])
    _upsert_option(LeadSource, client.lead_source)
    _upsert_option(Campaign, client.campaign)
    if client.funnel_status != old_funnel:
        content = "Etapa do funil: " + _fmt_log(old_funnel) + " -> " + _fmt_log(client.funnel_status)
        if client.funnel_status == "PERDIDO" and client.lost_reason:
            content += " — Motivo: " + client.lost_reason
        _log_interaction(client_id, "SISTEMA", content)
    if client.estimated_value != old_value:
        _log_interaction(client_id, "ORCAMENTO", "Valor estimado: " + _fmt_log(old_value) + " -> " + _fmt_log(client.estimated_value))
    if client.lead_source != old_source:
        _log_interaction(client_id, "OBSERVACAO", "Fonte do lead: " + _fmt_log(old_source) + " -> " + _fmt_log(client.lead_source))
    if client.campaign != old_campaign:
        _log_interaction(client_id, "OBSERVACAO", "Campanha: " + _fmt_log(old_campaign) + " -> " + _fmt_log(client.campaign))
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