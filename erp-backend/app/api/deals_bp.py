"""Negociacoes (deals) do funil de vendas — o CARD separado do CADASTRO (multi-card, out/2026).

Cada Deal e um card: client_id + funnel_id + etapa + valores + flags de
conclusao + vendedor/parceiro. O cliente vira so cadastro; N deals do mesmo
cliente coexistem no mesmo funil (ex.: Elisandra com 2 vendas).

Compatibilidade (Fase B): escrita espelhada no cliente (ultimo deal tocado
espelha funnel/status/valores/flags no Client) para o kanban antigo e os
relatorios legados continuarem funcionando; o PUT legado de /api/clients
garante o deal principal via _ensure_principal_deal (em clients_bp).
Remocao do espelho vira Fase E, com uso validado.
"""

from datetime import date, timedelta

from flask import Blueprint, g, jsonify

from app.helpers import body_json, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    Client,
    Deal,
    Funnel,
    FunnelColumn,
    LeadSource,
    Campaign,
    Partner,
    Project,
    User,
    next_sale_code,
    utcnow,
)

bp = Blueprint("deals", __name__)


def _upsert_option(model, name):
    name = (name or "").strip()
    if not name:
        return
    existing = db.session.query(model).filter_by(name=name).first()
    if not existing:
        db.session.add(model(name=name))


def _log(client_id, itype, content):
    db.session.add(
        __import__("app.models.models", fromlist=["Interaction"]).Interaction(
            client_id=client_id, type=itype, content=content, automatic=True
        )
    )


def _default_crm_funnel():
    return db.session.query(Funnel).filter_by(kind="CRM", is_default=True).first()


def _first_status(funnel_id):
    col = (
        db.session.query(FunnelColumn)
        .filter_by(funnel_id=funnel_id)
        .order_by(FunnelColumn.position)
        .first()
    )
    return col.column_key if col else "PROSPECCAO"


def _mirror_to_client(deal):
    """Espelha o deal tocado no cliente (compat com kanban/relatorios legados)."""
    client = db.session.get(Client, deal.client_id)
    if not client:
        return
    client.funnel_id = deal.funnel_id
    client.funnel_status = deal.funnel_status
    client.estimated_value = deal.estimated_value
    client.lost_reason = deal.lost_reason
    client.seller_id = deal.seller_id
    client.partner_id = deal.partner_id
    client.lead_source = deal.lead_source
    client.campaign = deal.campaign
    client.sale_concluded_at = deal.sale_concluded_at
    client.closed_at = deal.closed_at


def _resolve_funnel(fid_raw, default_id=None):
    if fid_raw in (None, ""):
        return default_id
    fid = str(fid_raw).strip()
    funnel = db.session.get(Funnel, fid)
    if not funnel or funnel.kind != "CRM" or not funnel.active:
        return "invalid"
    return fid


@bp.get("/api/deals")
@token_required()
def list_deals():
    q = db.session.query(Deal)
    fid = (request_args_get("funnel_id") or "").strip()
    if fid:
        q = q.filter(Deal.funnel_id == fid)
    cid = (request_args_get("client_id") or "").strip()
    if cid:
        q = q.filter(Deal.client_id == cid)
    rows = q.order_by(Deal.created_at.desc()).all()
    return jsonify([d.to_dict() for d in rows])


def request_args_get(name):
    from flask import request as _rq

    return _rq.args.get(name)


@bp.post("/api/deals")
@token_required()
def create_deal():
    from app.models.models import Sale as SaleModel  # noqa: F401 (garante tabela no contexto)

    data = body_json()
    client = db.session.get(Client, (data.get("client_id") or "").strip())
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404

    default_funnel = _default_crm_funnel()
    default_id = default_funnel.id if default_funnel else None
    fid = _resolve_funnel(data.get("funnel_id"), default_id)
    if fid == "invalid":
        return jsonify({"detail": "funnel_id invalido"}), 400
    if not fid:
        return jsonify({"detail": "Nenhum funil CRM disponivel"}), 400

    status = (data.get("funnel_status") or "").strip() or _first_status(fid)
    title = (data.get("title") or "").strip() or f"Negociacao - {client.name}"
    title = title[:200]

    deal = Deal(
        client_id=client.id,
        funnel_id=fid,
        funnel_status=status[:60],
        title=title,
    )
    if "estimated_value" in data:
        try:
            deal.estimated_value = float(data["estimated_value"]) if data["estimated_value"] not in (None, "") else None
        except (TypeError, ValueError):
            return jsonify({"detail": "estimated_value invalido"}), 400
    if "lost_reason" in data:
        deal.lost_reason = data.get("lost_reason") or None
    if "lead_source" in data:
        deal.lead_source = (data.get("lead_source") or "").strip()
    if "campaign" in data:
        deal.campaign = (data.get("campaign") or "").strip()
    if "seller_id" in data:
        raw = data.get("seller_id")
        if raw in (None, ""):
            deal.seller_id = None
        else:
            if not db.session.get(User, str(raw).strip()):
                return jsonify({"detail": "Vendedor nao encontrado"}), 404
            deal.seller_id = str(raw).strip()
    elif client.seller_id:
        deal.seller_id = client.seller_id
    if "partner_id" in data:
        raw = data.get("partner_id")
        if raw in (None, ""):
            deal.partner_id = None
        else:
            if not db.session.get(Partner, str(raw).strip()):
                return jsonify({"detail": "Parceiro nao encontrado"}), 404
            deal.partner_id = str(raw).strip()
    elif client.partner_id:
        deal.partner_id = client.partner_id
    if not deal.lead_source and client.lead_source:
        deal.lead_source = client.lead_source
    if not deal.campaign and client.campaign:
        deal.campaign = client.campaign

    _upsert_option(LeadSource, deal.lead_source)
    _upsert_option(Campaign, deal.campaign)
    db.session.add(deal)
    db.session.flush()
    _mirror_to_client(deal)
    _log(client.id, "SISTEMA", f"Nova negociacao no funil: {deal.title} ({deal.funnel_status}).")
    db.session.commit()
    return jsonify(deal.to_dict()), 201


@bp.get("/api/deals/<deal_id>")
@token_required()
def get_deal(deal_id):
    deal = db.session.get(Deal, deal_id)
    if not deal:
        return jsonify({"detail": "Negociacao nao encontrada"}), 404
    return jsonify(deal.to_dict())


@bp.put("/api/deals/<deal_id>")
@token_required()
def update_deal(deal_id):
    deal = db.session.get(Deal, deal_id)
    if not deal:
        return jsonify({"detail": "Negociacao nao encontrada"}), 404
    data = body_json()
    old_status = deal.funnel_status

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"detail": "title e obrigatorio"}), 400
        deal.title = title[:200]
    if "funnel_id" in data:
        raw = data.get("funnel_id")
        if raw is None:
            return jsonify({"detail": "funnel_id nao pode ser nulo (exclua o card)"}), 400
        fid = _resolve_funnel(raw)
        if fid == "invalid" or not fid:
            return jsonify({"detail": "funnel_id invalido"}), 400
        deal.funnel_id = fid
    if "funnel_status" in data:
        status = (data.get("funnel_status") or "").strip()
        if not status:
            return jsonify({"detail": "funnel_status e obrigatorio"}), 400
        deal.funnel_status = status[:60]
    if "estimated_value" in data:
        raw = data.get("estimated_value")
        if raw in (None, ""):
            deal.estimated_value = None
        else:
            try:
                deal.estimated_value = float(raw)
            except (TypeError, ValueError):
                return jsonify({"detail": "estimated_value invalido"}), 400
    if "lost_reason" in data:
        deal.lost_reason = data.get("lost_reason") or None
    if "lead_source" in data:
        deal.lead_source = (data.get("lead_source") or "").strip()
    if "campaign" in data:
        deal.campaign = (data.get("campaign") or "").strip()
    if "seller_id" in data:
        raw = data.get("seller_id")
        if raw in (None, ""):
            deal.seller_id = None
        else:
            if not db.session.get(User, str(raw).strip()):
                return jsonify({"detail": "Vendedor nao encontrado"}), 404
            deal.seller_id = str(raw).strip()
    if "partner_id" in data:
        raw = data.get("partner_id")
        if raw in (None, ""):
            deal.partner_id = None
        else:
            if not db.session.get(Partner, str(raw).strip()):
                return jsonify({"detail": "Parceiro nao encontrado"}), 404
            deal.partner_id = str(raw).strip()

    _upsert_option(LeadSource, deal.lead_source)
    _upsert_option(Campaign, deal.campaign)
    if deal.funnel_status != old_status:
        _log(deal.client_id, "SISTEMA", f"Negociacao {deal.title}: etapa {old_status} -> {deal.funnel_status}.")
    _mirror_to_client(deal)
    db.session.commit()
    return jsonify(deal.to_dict())


@bp.delete("/api/deals/<deal_id>")
@token_required()
def delete_deal(deal_id):
    from app.models.models import Sale as SaleModel

    deal = db.session.get(Deal, deal_id)
    if not deal:
        return jsonify({"detail": "Negociacao nao encontrada"}), 404
    if db.session.query(SaleModel).filter_by(deal_id=deal.id).count():
        return jsonify({"detail": "Negociacao possui venda gerada — exclua a venda antes"}), 400
    client_id = deal.client_id
    # Producao continua: so desvincula o deal dos cards.
    for p in db.session.query(Project).filter_by(deal_id=deal.id).all():
        p.deal_id = None
    db.session.delete(deal)
    db.session.flush()
    # Espelho: mostra outro deal do cliente no legado, ou volta ao cadastro.
    rest = (
        db.session.query(Deal)
        .filter_by(client_id=client_id)
        .order_by(Deal.created_at.desc())
        .all()
    )
    client = db.session.get(Client, client_id)
    if client is not None:
        if rest:
            _mirror_to_client(rest[0])
        else:
            client.funnel_id = None
            client.sale_concluded_at = None
            client.closed_at = None
    if client is not None:
        _log(client_id, "SISTEMA", f"Negociacao excluida do funil: {deal.title}.")
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/deals/<deal_id>/conclude-sale")
@token_required()
def deal_conclude_sale(deal_id):
    """Botao Concluir venda do card (deal): marca flags + cria projeto na Producao."""
    deal = db.session.get(Deal, deal_id)
    if not deal:
        return jsonify({"detail": "Negociacao nao encontrada"}), 404
    client = db.session.get(Client, deal.client_id)
    data = body_json()
    title = (data.get("title") or "").strip() or f"Projeto - {client.name if client else deal.title}"
    raw_value = data.get("value")
    if raw_value in (None, ""):
        raw_value = num(deal.estimated_value) or 0
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return jsonify({"detail": "value invalido"}), 400

    funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
    if not funnel:
        return jsonify({"detail": "Funil de Producao nao encontrado"}), 400
    cols = (
        db.session.query(FunnelColumn)
        .filter_by(funnel_id=funnel.id)
        .order_by(FunnelColumn.position)
        .all()
    )
    first_key = cols[0].column_key if cols else "ORCAMENTO"
    deadline = parse_date(data.get("deadline"))
    if deadline is None:
        deadline = date.today() + timedelta(days=30)

    if deal.sale_concluded_at is None:
        deal.sale_concluded_at = utcnow()
    if deal.closed_at is None:
        deal.closed_at = deal.sale_concluded_at
        if client is not None:
            _log(client.id, "SISTEMA",
                 f"Venda concluída pelo botão Concluir venda ({title}, R$ {value:,.2f}) — projeto criado na Produção.")

    project = Project(
        title=title,
        client_id=deal.client_id,
        description=data.get("description") or "",
        status=first_key,
        value=value,
        deadline=deadline,
        steps=data.get("steps") or [],
        funnel_id=funnel.id,
        deal_id=deal.id,
    )
    db.session.add(project)
    _mirror_to_client(deal)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@bp.post("/api/deals/<deal_id>/register-direct-sale")
@token_required(roles=["ADMIN", "GERENTE"])
def deal_register_direct_sale(deal_id):
    """Botao Registrar venda do FECHAMENTO (deal): cria Sale sem financeiro/producao."""
    from app.models.models import Sale

    deal = db.session.get(Deal, deal_id)
    if not deal:
        return jsonify({"detail": "Negociacao nao encontrada"}), 404
    client = db.session.get(Client, deal.client_id)
    data = body_json() or {}
    sale_date = parse_date(data.get("sale_date")) or date.today()
    raw_value = data.get("total_value")
    if raw_value in (None, ""):
        raw_value = num(deal.estimated_value) or 0
    try:
        total_value = float(raw_value)
    except (TypeError, ValueError):
        return jsonify({"detail": "total_value invalido"}), 400
    if total_value <= 0:
        return jsonify({"detail": "Informe o valor da venda (negociacao sem valor)"}), 400

    if deal.sale_concluded_at is None:
        deal.sale_concluded_at = utcnow()
    if deal.closed_at is None:
        deal.closed_at = deal.sale_concluded_at

    sale = Sale(
        code=next_sale_code(),
        client_id=deal.client_id,
        deal_id=deal.id,
        seller_id=deal.seller_id,
        partner_id=deal.partner_id,
        lead_source=(deal.lead_source or ""),
        sale_date=sale_date,
        total_value=total_value,
        down_payment=0,
        installments=0,
        installment_value=0,
        address=(client.address if client and client.address else ""),
        created_by=getattr(g, "current_user", None).username if getattr(g, "current_user", None) else "",
    )
    db.session.add(sale)
    db.session.flush()
    if client is not None:
        _log(client.id, "SISTEMA",
             f"Venda {sale.code} registrada sem producao (R$ {total_value:,.2f}) — negociacao {deal.title}.")
    _mirror_to_client(deal)
    db.session.commit()
    return jsonify(sale.to_dict()), 201


@bp.post("/api/deals/<deal_id>/mark-lost")
@token_required(roles=["ADMIN", "GERENTE"])
def deal_mark_lost(deal_id):
    """Botao Marcar como perdida do card (deal): vai p/ PERDIDO, limpa flags."""
    from app.models.models import Sale as SaleModel

    deal = db.session.get(Deal, deal_id)
    if not deal:
        return jsonify({"detail": "Negociacao nao encontrada"}), 404
    data = body_json() or {}
    reason = (data.get("lost_reason") or "").strip()

    if db.session.query(SaleModel).filter_by(deal_id=deal.id).count():
        return jsonify({"detail": "Negociacao possui venda gerada — exclua a venda antes de marcar como perdida"}), 400

    funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
    first_key = "ORCAMENTO"
    if funnel:
        col = (
            db.session.query(FunnelColumn)
            .filter_by(funnel_id=funnel.id)
            .order_by(FunnelColumn.position)
            .first()
        )
        if col:
            first_key = col.column_key

    projects = db.session.query(Project).filter_by(deal_id=deal.id).all()
    started = [p for p in projects
               if p.start_date is not None or p.concluded_at is not None or p.status != first_key]
    if started:
        return jsonify({"detail": "Negociacao possui projeto ja iniciado na Producao — resolva a producao antes"}), 400
    deleted = len(projects)
    for p in projects:
        db.session.delete(p)

    old = deal.funnel_status
    deal.funnel_status = "PERDIDO"
    deal.lost_reason = reason or None
    deal.closed_at = None
    deal.sale_concluded_at = None
    _log(deal.client_id, "SISTEMA",
         f"Negociacao {deal.title} marcada como perdida (etapa: {old} -> PERDIDO)"
         + (f" — Motivo: {reason}" if reason else "")
         + (f" {deleted} projeto(s) nao iniciado(s) excluido(s)." if deleted else ""))
    _mirror_to_client(deal)
    db.session.commit()
    return jsonify(deal.to_dict())
