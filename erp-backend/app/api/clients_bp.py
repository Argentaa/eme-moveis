"""CRUD /api/clients."""
import math
from datetime import date, timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa

from app.helpers import body_json, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    Attachment,
    CalendarEvent,
    Campaign,
    Client,
    Funnel,
    FunnelColumn,
    is_lost_status,
    is_won_status,
    Interaction,
    LeadSource,
    NegotiationItem,
    Partner,
    Product,
    utcnow,
    Project,
    User,
)

bp = Blueprint("clients", __name__)

CLIENT_FIELDS = (
    "name", "email", "phone", "cpf_cnpj", "address",
    "funnel_status", "lost_reason", "estimated_value", "lead_source", "campaign",
    "funnel_id", "partner_id", "seller_id",
    "is_supplier", "contact", "category", "payment_terms", "avg_delivery_days",
)

SUPPLIER_OPTIONAL_FIELDS = ("contact", "category", "payment_terms")

INTERACTION_TYPES = ("CONVERSA", "PROPOSTA", "ORCAMENTO", "OBSERVACAO",
                     # Fase 8 (check-ins de pos-venda): contato proativo pos-entrega.
                     # LIGACAO/VISITA/WHATSAPP entram aqui para o historico nao
                     # coagir tudo para OBSERVACAO.
                     "LIGACAO", "VISITA", "WHATSAPP")

ITEM_RECURRENCES = ("UNICO", "MENSAL", "TRIMESTRAL", "ANUAL")


def _apply_supplier_fields(row, data):
    """Aplica campos de fornecedor no modelo Client, com validacao."""
    if "is_supplier" in data:
        v = data.get("is_supplier")
        if isinstance(v, str):
            v = v.strip().lower() in ("1", "true", "sim", "yes", "on")
        row.is_supplier = bool(v)
    for f in SUPPLIER_OPTIONAL_FIELDS:
        if f in data:
            v = data[f]
            setattr(row, f, v.strip() if isinstance(v, str) else v)
    if "avg_delivery_days" in data:
        v = data.get("avg_delivery_days")
        if v is None or v == "":
            row.avg_delivery_days = None
        else:
            try:
                iv = int(v)
            except (TypeError, ValueError):
                raise ValueError("avg_delivery_days deve ser inteiro >= 0")
            if iv < 0:
                raise ValueError("avg_delivery_days deve ser inteiro >= 0")
            row.avg_delivery_days = iv


def ensure_supplier_mirror(client):
    """Mantem a linha espelho em suppliers para cliente marcado como fornecedor.

    Preserva as FKs existentes: Compras/Financeiro continuam usando
    supplier_id (id do espelho), nunca o client id direto. Nao quebra a
    criacao do cliente se o espelho falhar (log + rollback parcial).
    """
    if not getattr(client, "is_supplier", False):
        return None
    try:
        from app.models.models import Supplier as SupplierModel
        mirror = db.session.query(SupplierModel).filter_by(client_id=client.id).first()
        if not mirror:
            mirror = SupplierModel(client_id=client.id)
            db.session.add(mirror)
        mirror.name = client.name
        mirror.cnpj = client.cpf_cnpj or ""
        mirror.contact = client.contact or ""
        mirror.phone = client.phone or ""
        mirror.email = client.email or ""
        mirror.address = client.address or ""
        mirror.category = client.category or ""
        mirror.payment_terms = client.payment_terms or ""
        mirror.avg_delivery_days = client.avg_delivery_days
        db.session.commit()
        return mirror
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        import logging
        logging.getLogger(__name__).exception("Espelho de fornecedor falhou p/ cliente %s", getattr(client, "id", "?"))
        return None


def _item_number(value, default):
    """Converte valor numerico de item; default quando ausente, erro se invalido/negativo."""
    if value is None:
        return default
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError("numero invalido")
    if not math.isfinite(n) or n < 0:
        raise ValueError("numero invalido")
    return n


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


def _resolve_funnel_id_for_create(data):
    # Cadastro central pode criar cliente SEM funil: funnel_id explicitamente
    # null significa "só cadastro" (o Comercial importa depois). Ausente ou
    # string vazia mantem o comportamento legado (funil CRM padrao).
    if "funnel_id" not in data:
        funnel = db.session.query(Funnel).filter_by(kind="CRM", is_default=True).first()
        return funnel.id if funnel else None
    raw = data.get("funnel_id")
    if raw is None:
        return None
    if isinstance(raw, str) and str(raw).strip() == "":
        funnel = db.session.query(Funnel).filter_by(kind="CRM", is_default=True).first()
        return funnel.id if funnel else None
    fid = str(raw).strip()
    funnel = db.session.get(Funnel, fid)
    if not funnel or funnel.kind != "CRM" or not funnel.active:
        return "invalid"
    return fid


@bp.get("/api/clients")
@token_required()
def list_clients():
    q = db.session.query(Client)
    is_supplier = (request.args.get("is_supplier") or "").strip().lower()
    if is_supplier in ("1", "true", "sim", "yes", "on"):
        q = q.filter(Client.is_supplier.is_(True))
    elif is_supplier in ("0", "false", "nao", "no", "off"):
        q = q.filter(Client.is_supplier.is_(False))
    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(sa.or_(
            Client.name.ilike(like),
            Client.email.ilike(like),
            Client.phone.ilike(like),
            Client.cpf_cnpj.ilike(like),
        ))
    clients = q.order_by(Client.created_at.desc()).all()
    return jsonify([c.to_dict() for c in clients])


@bp.post("/api/clients")
@token_required()
def create_client():
    data = body_json()
    if not (data.get("name") or "").strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    client = Client()
    for f in CLIENT_FIELDS:
        if f in ("funnel_id", "partner_id", "seller_id"):
            continue
        if f in ("is_supplier", "contact", "category", "payment_terms", "avg_delivery_days"):
            continue
        if f in data:
            setattr(client, f, data[f] if data[f] != "" or f in ("email", "phone", "address") else None)
    try:
        _apply_supplier_fields(client, data)
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    if not client.cpf_cnpj:
        client.cpf_cnpj = None
    if not client.funnel_status:
        client.funnel_status = "PROSPECCAO"
    funnel_resolved = _resolve_funnel_id_for_create(data)
    if funnel_resolved == "invalid":
        return jsonify({"detail": "funnel_id invalido"}), 400
    client.funnel_id = funnel_resolved
    if "partner_id" in data:
        raw = data.get("partner_id")
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            client.partner_id = None
        else:
            pid = str(raw).strip()
            if not db.session.get(Partner, pid):
                return jsonify({"detail": "Parceiro nao encontrado"}), 404
            client.partner_id = pid
    if "seller_id" in data:
        raw = data.get("seller_id")
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            client.seller_id = None
        else:
            sid = str(raw).strip()
            if not db.session.get(User, sid):
                return jsonify({"detail": "Vendedor nao encontrado"}), 404
            client.seller_id = sid
    _upsert_option(LeadSource, client.lead_source)
    _upsert_option(Campaign, client.campaign)
    db.session.add(client)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "cpf_cnpj ja cadastrado"}), 400
    ensure_supplier_mirror(client)
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
    if not db.session.get(Client, client_id):
        return jsonify({"detail": "Cliente nao encontrado"}), 404
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


@bp.get("/api/clients/<client_id>/items")
@token_required()
def list_items(client_id):
    """Lista os itens da negociacao de um cliente."""
    rows = (db.session.query(NegotiationItem).filter_by(client_id=client_id)
            .order_by(NegotiationItem.created_at).all())
    return jsonify([it.to_dict() for it in rows])


@bp.post("/api/clients/<client_id>/items")
@token_required()
def create_item(client_id):
    """Cria um item de negociacao para o cliente (vincula ou cria o produto)."""
    if not db.session.get(Client, client_id):
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    data = body_json()
    name = (data.get("name") or "").strip()
    product_id = data.get("product_id")
    if product_id:
        prod = db.session.get(Product, product_id)
        if not prod:
            return jsonify({"detail": "Produto nao encontrado"}), 404
        if not name:
            name = prod.name
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    try:
        qty = _item_number(data.get("quantity"), 1)
        price = _item_number(data.get("unit_price"), 0)
    except ValueError:
        return jsonify({"detail": "numero invalido"}), 400
    rec = (data.get("recurrence") or "UNICO").upper()
    if rec not in ITEM_RECURRENCES:
        rec = "UNICO"
    if not product_id:
        prod = db.session.query(Product).filter_by(name=name).first()
        if not prod:
            prod = Product(name=name, default_price=price)
            db.session.add(prod)
            db.session.flush()
        product_id = prod.id
    item = NegotiationItem(client_id=client_id, product_id=product_id, name=name,
                           quantity=qty, unit_price=price, recurrence=rec)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.put("/api/items/<item_id>")
@token_required()
def update_item(item_id):
    """Atualiza um item de negociacao existente."""
    item = db.session.get(NegotiationItem, item_id)
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"detail": "name e obrigatorio"}), 400
        item.name = name
    try:
        item.quantity = _item_number(data.get("quantity"), item.quantity)
        item.unit_price = _item_number(data.get("unit_price"), item.unit_price)
    except ValueError:
        return jsonify({"detail": "numero invalido"}), 400
    if "recurrence" in data:
        rec = (data.get("recurrence") or "UNICO").upper()
        item.recurrence = rec if rec in ITEM_RECURRENCES else "UNICO"
    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/api/items/<item_id>")
@token_required()
def delete_item(item_id):
    """Remove um item de negociacao."""
    item = db.session.get(NegotiationItem, item_id)
    if not item:
        return jsonify({"detail": "Item nao encontrado"}), 404
    db.session.delete(item)
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
        if f in ("funnel_id", "partner_id", "seller_id"):
            continue
        if f in ("is_supplier", "contact", "category", "payment_terms", "avg_delivery_days"):
            continue
        if f in data:
            setattr(client, f, data[f])
    try:
        _apply_supplier_fields(client, data)
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    if "funnel_id" in data:
        raw = data.get("funnel_id")
        if raw is None:
            # Desvincular do funil (botao Excluir no Comercial): mantem o
            # cadastro no central, so sai do funil.
            client.funnel_id = None
        elif isinstance(raw, str) and str(raw).strip() == "":
            funnel = db.session.query(Funnel).filter_by(kind="CRM", is_default=True).first()
            client.funnel_id = funnel.id if funnel else None
        else:
            fid = str(raw).strip()
            funnel = db.session.get(Funnel, fid)
            if not funnel or funnel.kind != "CRM" or not funnel.active:
                return jsonify({"detail": "funnel_id invalido"}), 400
            client.funnel_id = fid
            # Reabertura de negociacao (out/2026): vincular ao funil um cliente
            # com venda concluida limpa as flags de conclusao para o card
            # voltar ao kanban como nova negociacao. O historico nao se perde:
            # a venda concluida permanece em Vendas realizadas (tabela Sale) e
            # nas metas por data da venda; sem a limpeza o cliente ficava no
            # limbo — invisivel no kanban (filtro de concluidos) e fora do
            # select de vincular (ja esta neste funil). Caso real: Elisandra
            # Lucas, venda entregue, sem caminho para nova negociacao.
            if client.sale_concluded_at is not None or client.closed_at is not None:
                from app.models.models import Sale as SaleModel
                had_sale = db.session.query(SaleModel).filter_by(client_id=client.id).count() > 0
                client.sale_concluded_at = None
                client.closed_at = None
                _log_interaction(
                    client_id, "SISTEMA",
                    "Nova negociacao reaberta no funil — flags de conclusao limpas"
                    + (" (venda(s) anterior(es) preservada(s) em Vendas realizadas)." if had_sale else "."),
                )
    if "partner_id" in data:
        raw = data.get("partner_id")
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            client.partner_id = None
        else:
            pid = str(raw).strip()
            if not db.session.get(Partner, pid):
                return jsonify({"detail": "Parceiro nao encontrado"}), 404
            client.partner_id = pid
    if "seller_id" in data:
        raw = data.get("seller_id")
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            client.seller_id = None
        else:
            sid = str(raw).strip()
            if not db.session.get(User, sid):
                return jsonify({"detail": "Vendedor nao encontrado"}), 404
            client.seller_id = sid
    _upsert_option(LeadSource, client.lead_source)
    _upsert_option(Campaign, client.campaign)
    if client.funnel_status != old_funnel:
        content = "Etapa do funil: " + _fmt_log(old_funnel) + " -> " + _fmt_log(client.funnel_status)
        if client.funnel_status == "PERDIDO" and client.lost_reason:
            content += " — Motivo: " + client.lost_reason
        _log_interaction(client_id, "SISTEMA", content)
    if is_lost_status(client.funnel_status):
        # Perdido nao e realizado: card em etapa de perda nao pode carregar
        # datas de conclusao, senao o perdido continua na meta comercial
        # (via closed_at) e nas pendencias de geracao do CRM. Com Sale
        # existente a meta por sale_date nao muda (a Sale segue contando).
        if client.sale_concluded_at is not None or client.closed_at is not None:
            client.sale_concluded_at = None
            client.closed_at = None
            _log_interaction(client_id, "SISTEMA",
                             "Etapa de perda — datas de conclusao limpas (perdido nao e venda realizada).")
    if client.estimated_value != old_value:
        _log_interaction(client_id, "ORCAMENTO", "Valor estimado: " + _fmt_log(old_value) + " -> " + _fmt_log(client.estimated_value))
    if client.lead_source != old_source:
        _log_interaction(client_id, "OBSERVACAO", "Fonte do lead: " + _fmt_log(old_source) + " -> " + _fmt_log(client.lead_source))
    if client.campaign != old_campaign:
        _log_interaction(client_id, "OBSERVACAO", "Campanha: " + _fmt_log(old_campaign) + " -> " + _fmt_log(client.campaign))
    # Automacao de venda fechada REMOVIDA (2026-10-01): arrastar o card para a
    # etapa de ganho nao atualiza mais meta/comissao/CRM nem cria projeto — a
    # venda passa a ser gerada na tela "Gerar venda" (POST /api/sales), que
    # grava sale_concluded_at/closed_at e cria contas a receber + producao.
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "cpf_cnpj ja cadastrado"}), 400
    ensure_supplier_mirror(client)
    return jsonify(client.to_dict())


@bp.post("/api/clients/<client_id>/conclude-sale")
@token_required()
def conclude_sale(client_id):
    """Botao "Concluir venda" do Comercial.

    Faz as duas coisas numa transacao so: marca a venda como concluida (o card
    sai do funil de vendas) e cria o projeto na Producao. Separadas, "vender"
    virava dois passos manuais e o projeto podia nascer sem vinculo com a venda
    — ou a venda ficar marcada como ganha sem nada em producao.

    A conclusao e a flag `sale_concluded_at`, NAO a coluna do funil: as colunas
    sao renomeadas pelo cliente e a chave nao e confiavel.
    """
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404

    data = body_json()
    title = (data.get("title") or "").strip() or f"Projeto - {client.name}"
    raw_value = data.get("value")
    if raw_value in (None, ""):
        raw_value = num(client.negotiation_value) or num(client.estimated_value) or 0
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return jsonify({"detail": "value invalido"}), 400

    funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
    if not funnel:
        return jsonify({"detail": "Funil de Producao nao encontrado"}), 400

    # Primeira coluna do funil (por posicao): o projeto nasce no inicio da
    # Producao. O resto do caminho e o operador quem move.
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

    if client.sale_concluded_at is None:
        client.sale_concluded_at = utcnow()

    # closed_at e a base da meta comercial, da comissao e dos relatorios de
    # CRM: sem ele, a venda concluida pelo botao criava o projeto na Producao
    # mas nao aparecia em nenhum dashboard (bug real: venda de R$ 12.570
    # concluida pelo botao, projeto criado, zero nos painéis). O caminho pelo
    # funil grava closed_at na automacao do update; o botao precisa do mesmo.
    if client.closed_at is None:
        client.closed_at = client.sale_concluded_at
        _log_interaction(
            client.id, "SISTEMA",
            f"Venda concluída pelo botão Concluir venda ({title}, "
            f"R$ {value:,.2f}) — projeto criado na Produção.",
        )

    project = Project(
        title=title,
        client_id=client.id,
        description=data.get("description") or "",
        status=first_key,
        value=value,
        deadline=deadline,
        steps=data.get("steps") or [],
        funnel_id=funnel.id,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@bp.post("/api/clients/<client_id>/register-direct-sale")
@token_required(roles=["ADMIN", "GERENTE"])
def register_direct_sale(client_id):
    """Botao "Registrar venda" do FECHAMENTO: venda já produzida/entregue.

    Cria a `Sale` (entra em Vendas, metas, comissao e CRM via closed_at) SEM
    financeiro e SEM projeto na Producao — pedido do dono (2026-10-06). O card
    sai do funil pela mesma flag do conclude-sale (`sale_concluded_at`).
    body {sale_date?, total_value?}: default hoje + negotiation/estimated.
    """
    from app.models.models import Sale

    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    data = body_json() or {}
    sale_date = parse_date(data.get("sale_date")) or date.today()
    raw_value = data.get("total_value")
    if raw_value in (None, ""):
        raw_value = num(client.negotiation_value) or num(client.estimated_value) or 0
    try:
        total_value = float(raw_value)
    except (TypeError, ValueError):
        return jsonify({"detail": "total_value invalido"}), 400
    if total_value <= 0:
        return jsonify({"detail": "Informe o valor da venda (card sem valor)"}), 400

    if client.sale_concluded_at is None:
        client.sale_concluded_at = utcnow()
    if client.closed_at is None:
        client.closed_at = client.sale_concluded_at

    n = db.session.query(Sale).count()
    sale = Sale(
        code="V-%04d" % (n + 1),
        client_id=client.id,
        seller_id=client.seller_id,
        partner_id=client.partner_id,
        lead_source=(client.lead_source or ""),
        sale_date=sale_date,
        total_value=total_value,
        down_payment=0,
        installments=0,
        installment_value=0,
        address=(client.address or ""),
        created_by=getattr(g, "current_user", None).username if getattr(g, "current_user", None) else "",
    )
    db.session.add(sale)
    db.session.flush()
    _log_interaction(
        client.id, "SISTEMA",
        f"Venda {sale.code} registrada sem producao (R$ {total_value:,.2f}) — "
        "card do FECHAMENTO passado direto para Vendas, sem financeiro.",
    )
    db.session.commit()
    return jsonify(sale.to_dict()), 201


@bp.post("/api/clients/<client_id>/mark-lost")
@token_required(roles=["ADMIN", "GERENTE"])
def mark_lost(client_id):
    """Botao "Marcar como perdida" do FECHAMENTO: fechado sem venda em 1 clique.

    Para cliente fechado (conclude-sale) que nao virou venda: move o card para
    PERDIDO, limpa closed_at/sale_concluded_at (sai da meta comercial e das
    pendencias de geracao do CRM) e deleta o projeto da Producao ainda nao
    iniciado. 400 se o cliente tem alguma Sale (orienta excluir a venda
    antes) ou se o projeto ja foi iniciado (pede resolver a producao antes).
    """
    from app.models.models import Sale

    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404

    data = body_json() or {}
    reason = (data.get("lost_reason") or "").strip()

    if db.session.query(Sale).filter_by(client_id=client.id).count():
        return jsonify({
            "detail": "Cliente possui venda gerada — use Excluir venda antes de marcar como perdida"
        }), 400

    # Coluna inicial do funil de Producao: projeto nela e sem start_date
    # ainda nao foi iniciado e pode ser descartado junto com a perda.
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

    projects = db.session.query(Project).filter_by(client_id=client.id).all()
    started = [
        p for p in projects
        if p.start_date is not None or p.concluded_at is not None or p.status != first_key
    ]
    if started:
        return jsonify({
            "detail": "Cliente possui projeto ja iniciado na Producao — resolva a producao antes de marcar como perdida"
        }), 400

    deleted = len(projects)
    for p in projects:
        db.session.delete(p)

    old_funnel = client.funnel_status
    client.funnel_status = "PERDIDO"
    client.lost_reason = reason or None
    client.closed_at = None
    client.sale_concluded_at = None
    content = (
        "Marcado como perdido (etapa: " + _fmt_log(old_funnel) + " -> PERDIDO)"
        + (" — Motivo: " + reason if reason else "")
        + " — datas de conclusao limpas (saiu da meta e das pendencias)."
    )
    if deleted:
        content += f" {deleted} projeto(s) nao iniciado(s) da Producao excluido(s)."
    _log_interaction(client.id, "SISTEMA", content)
    db.session.commit()
    return jsonify(client.to_dict())


@bp.delete("/api/clients/<client_id>")
@token_required()
def delete_client(client_id):
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    # Guard do cadastro central: cliente com historico nao pode ser excluido.
    # Depois de entrar no funil/producao, o registro vira referencia para
    # Compras, Financeiro, Agenda, Pos-venda etc. — preservar o cadastro.
    from app.models.models import (
        Attachment as AttModel,
        CalendarEvent as EvModel,
        FinancialRecord as FinModel,
        Interaction as IntModel,
        NegotiationItem as ItemModel,
        PurchaseOrder as POModel,
        ServiceTicket as TickModel,
        Supplier as SupModel,
    )
    counts = {
        "projeto(s)": db.session.query(Project).filter_by(client_id=client_id).count(),
        "lancamento(s) financeiro(s)": db.session.query(FinModel).filter_by(client_id=client_id).count(),
        "evento(s) de agenda": db.session.query(EvModel).filter_by(client_id=client_id).count(),
        "chamado(s) de pos-venda": db.session.query(TickModel).filter_by(client_id=client_id).count(),
        "item(ns) de negociacao": db.session.query(ItemModel).filter_by(client_id=client_id).count(),
        "interacao(oes)": db.session.query(IntModel).filter_by(client_id=client_id).count(),
        "anexo(s)": db.session.query(AttModel).filter_by(client_id=client_id).count(),
    }
    # Espelho como fornecedor: pedidos/lancamentos vinculados ao espelho
    # tambem bloqueiam a exclusao do cliente.
    try:
        mirror = db.session.query(SupModel).filter_by(client_id=client_id).first()
        if mirror:
            po = db.session.query(POModel).filter_by(supplier_id=mirror.id).count()
            fs = db.session.query(FinModel).filter_by(supplier_id=mirror.id).count()
            if po:
                counts["pedido(s) de compra como fornecedor"] = po
            if fs:
                counts["lancamento(s) como fornecedor"] = fs
    except Exception:
        pass
    linked = {k: v for k, v in counts.items() if v}
    if linked:
        parts = ", ".join(f"{v} {k}" for k, v in linked.items())
        return jsonify({
            "detail": f"Cliente possui {parts} e nao pode ser excluido. "
                      "O cadastro central preserva o historico; remova os vinculos ou desative o registro."
        }), 400
    db.session.delete(client)
    db.session.commit()
    return jsonify({"ok": True})
