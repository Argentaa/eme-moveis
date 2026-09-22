"""CRUD /api/clients."""
import math

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    Attachment,
    CalendarEvent,
    Campaign,
    Client,
    Funnel,
    FunnelColumn,
    Interaction,
    LeadSource,
    NegotiationItem,
    Partner,
    Product,
    Project,
)

bp = Blueprint("clients", __name__)

CLIENT_FIELDS = (
    "name", "email", "phone", "cpf_cnpj", "address",
    "funnel_status", "lost_reason", "estimated_value", "lead_source", "campaign",
    "funnel_id", "partner_id",
    "is_supplier", "contact", "category", "payment_terms", "avg_delivery_days",
)

SUPPLIER_OPTIONAL_FIELDS = ("contact", "category", "payment_terms")

INTERACTION_TYPES = ("CONVERSA", "PROPOSTA", "ORCAMENTO", "OBSERVACAO")

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
        if f in ("funnel_id", "partner_id"):
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
        if f in ("funnel_id", "partner_id"):
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
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            funnel = db.session.query(Funnel).filter_by(kind="CRM", is_default=True).first()
            client.funnel_id = funnel.id if funnel else None
        else:
            fid = str(raw).strip()
            funnel = db.session.get(Funnel, fid)
            if not funnel or funnel.kind != "CRM" or not funnel.active:
                return jsonify({"detail": "funnel_id invalido"}), 400
            client.funnel_id = fid
    if "partner_id" in data:
        raw = data.get("partner_id")
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            client.partner_id = None
        else:
            pid = str(raw).strip()
            if not db.session.get(Partner, pid):
                return jsonify({"detail": "Parceiro nao encontrado"}), 404
            client.partner_id = pid
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
    # Automacao: venda fechada cria projeto (idempotente)
    if client.funnel_status != old_funnel and client.funnel_id:
        try:
            funnel = db.session.get(Funnel, client.funnel_id)
            if funnel and funnel.kind == "CRM":
                cols = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id).order_by(FunnelColumn.position.desc()).all()
                if cols:
                    last_key = cols[0].column_key
                    if client.funnel_status == last_key:
                        # Verifica se ja existe projeto ativo para este cliente (nao CONCLUIDO)
                        existing = db.session.query(Project).filter(Project.client_id == client.id, Project.status != "CONCLUIDO").first()
                        if not existing:
                            # Determinar valor: negotiation_value (soma itens) ou estimated_value
                            try:
                                val = client.negotiation_value
                            except:  # noqa: E722
                                val = None
                            if val is None:
                                val = client.estimated_value
                            # Steps default do projeto (mesmo de create_project)
                            default_steps = [{"id": "1", "label": "Orcamento apresentado", "completed": False}, {"id": "2", "label": "Orcamento aprovado", "completed": False}, {"id": "3", "label": "Medicao tecnica", "completed": False}, {"id": "4", "label": "Aguardando materiais", "completed": False}, {"id": "5", "label": "Corte e producao", "completed": False}, {"id": "6", "label": "Montagem", "completed": False}]
                            # Tentar pegar funnel default de PROJECTS para o projeto
                            proj_funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
                            proj = Project(title=client.name, client_id=client.id, description="", status="ORCAMENTO", value=val or 0, steps=default_steps, funnel_id=proj_funnel.id if proj_funnel else None)
                            db.session.add(proj)
                            # Nao commit aqui; commit externo vai persistir
        except Exception as e:
            # Nao quebrar o update do cliente se a automacao falhar; apenas log
            import logging; logging.getLogger(__name__).exception("Venda fechada automacao falhou: %s", e)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"detail": "cpf_cnpj ja cadastrado"}), 400
    ensure_supplier_mirror(client)
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
