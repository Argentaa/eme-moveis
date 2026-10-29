"""Venda do Comercial: gerar venda com automacoes.

POST /api/sales  — cria a venda (concluida de uma vez) e dispara:
  - clients.sale_concluded_at / closed_at (base da meta, comissao e CRM);
  - contas a receber no Financeiro (entrada + 1 lancamento por parcela,
    PENDENTE, com conta bancaria de destino e vencimento explicito);
  - cards na Producao: um Project por ambiente vendido (sale_id vinculado).

GET  /api/sales      — lista (client_name/seller_name/partner_name/bank).
GET  /api/sales/<id> — detalhe com ambientes, itens e parcelas.
PUT  /api/sales/<id> — edita sale_date/total_value/down_payment/
  installments(+installment_value); NÃO recalcula o financeiro e os cards
  de produção já gerados (trilha de auditoria).
DELETE /api/sales/<id> — apaga a Sale e limpa sale_concluded_at/closed_at
  do cliente quando ele fica sem nenhuma Sale; NÃO mexe em funnel_status.

Contrato financeiro: entrada + N x valor_parcela == valor_total (tolerancia
de centavos). Items (produtos vendidos) sao detalhamento informativo — a soma
nao precisa fechar com o total; a resposta traz items_total_diff.
"""
from datetime import date, timedelta

from flask import Blueprint, g, jsonify, request

from app.helpers import body_json, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    BankAccount,
    Client,
    Deal,
    FinancialRecord,
    Funnel,
    FunnelColumn,
    Partner,
    Product,
    Project,
    Sale,
    SaleEnvironment,
    SaleInstallment,
    SaleItem,
    User,
    utcnow,
)
from app.api.clients_bp import _log_interaction, _mirror_client_to_principal_deal

bp = Blueprint("sales", __name__)

WRITE_ROLES = ["ADMIN", "GERENTE"]

# Mesmos steps que o front usava ao concluir venda (producao).
STEPS_DEFAULT_PRODUCAO = [
    {"id": "1", "label": "Medição técnica in loco", "completed": False},
    {"id": "2", "label": "Apresentação e plano de corte 3D", "completed": False},
    {"id": "3", "label": "Corte e colagem de fita de borda", "completed": False},
    {"id": "4", "label": "Usinagem de furos e ferragens", "completed": False},
    {"id": "5", "label": "Montagem prévia fábrica", "completed": False},
    {"id": "6", "label": "Instalação final no cliente", "completed": False},
]

CATEGORIA_VENDA = "Venda de Móveis"
PLANO_CONTA_VENDA = "1.1"  # Venda de produtos (plano de contas importado)


def _resolve_code():
    from app.models.models import next_sale_code
    return next_sale_code()


def _first_production_status():
    funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
    if not funnel:
        return "ORCAMENTO", None
    col = (
        db.session.query(FunnelColumn)
        .filter_by(funnel_id=funnel.id)
        .order_by(FunnelColumn.position)
        .first()
    )
    return (col.column_key if col else "ORCAMENTO"), funnel.id


def _sale_detail(sale):
    d = sale.to_dict()
    d["items_total_diff"] = round(
        float(sale.total_value or 0) - sum(i.subtotal for i in sale.items), 2
    )
    d["projects"] = [p.title for p in sale.projects]
    return d


@bp.get("/api/sales")
@token_required()
def list_sales():
    rows = db.session.query(Sale).order_by(Sale.concluded_at.desc()).all()
    return jsonify([{"id": s.id, "code": s.code, "client_id": s.client_id,
                     "client_name": s.client.name if s.client else None,
                     "sale_date": s.sale_date.isoformat(),
                     "total_value": num(s.total_value),
                     "seller_name": s.seller.username if s.seller else None,
                     "partner_name": s.partner.name if s.partner else None,
                     "concluded_at": s.concluded_at.isoformat() if s.concluded_at else None,
                     "delivery_date": s.delivery_date.isoformat() if s.delivery_date else None}
                    for s in rows])


@bp.get("/api/sales/<sale_id>")
@token_required()
def get_sale(sale_id):
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify({"detail": "Venda nao encontrada"}), 404
    return jsonify(_sale_detail(sale))


@bp.post("/api/sales")
@token_required(roles=WRITE_ROLES)
def create_sale():
    data = body_json()

    deal = None
    if data.get("deal_id"):
        deal = db.session.get(Deal, str(data.get("deal_id")).strip())
        if not deal:
            return jsonify({"detail": "Negociacao nao encontrada"}), 404

    client = db.session.get(Client, data.get("client_id") or (deal.client_id if deal else ""))
    if not client:
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    if deal is not None and deal.client_id != client.id:
        return jsonify({"detail": "Negociacao nao pertence a este cliente"}), 400
    if deal is None:
        # Chamada legada sem deal_id: com 1 unico deal, a venda e dele
        # (vincula + marca flags; sem isso o deal principal ficava sem data
        # e caia em `undated`). Com N deals, nao ha como saber qual — fica
        # sem vinculo (conservador: sem atribuicao errada).
        only = db.session.query(Deal).filter_by(client_id=client.id).all()
        if len(only) == 1:
            deal = only[0]

    seller = None
    if data.get("seller_id"):
        seller = db.session.get(User, data["seller_id"])
        if not seller:
            return jsonify({"detail": "Vendedor nao encontrado"}), 404
    partner = None
    if data.get("partner_id"):
        partner = db.session.get(Partner, data["partner_id"])
        if not partner:
            return jsonify({"detail": "Parceiro nao encontrado"}), 404
    bank = None
    if data.get("bank_account_id"):
        bank = db.session.get(BankAccount, data["bank_account_id"])
        if not bank:
            return jsonify({"detail": "Conta bancaria nao encontrada"}), 404

    sale_date = parse_date(data.get("sale_date"))
    if sale_date is None:
        return jsonify({"detail": "sale_date e obrigatoria (formato AAAA-MM-DD)"}), 400
    try:
        total_value = float(data.get("total_value") or 0)
    except (TypeError, ValueError):
        return jsonify({"detail": "total_value invalido"}), 400
    if total_value <= 0:
        return jsonify({"detail": "total_value deve ser maior que zero"}), 400
    try:
        down_payment = float(data.get("down_payment") or 0)
    except (TypeError, ValueError):
        down_payment = 0.0
    if down_payment < 0:
        return jsonify({"detail": "down_payment nao pode ser negativo"}), 400
    try:
        installments = int(data.get("installments") or 0)
    except (TypeError, ValueError):
        return jsonify({"detail": "installments invalido"}), 400
    if installments < 0 or installments > 60:
        return jsonify({"detail": "installments deve estar entre 0 e 60"}), 400
    try:
        installment_value = float(data.get("installment_value") or 0)
    except (TypeError, ValueError):
        installment_value = 0.0
    if installment_value < 0:
        return jsonify({"detail": "installment_value nao pode ser negativo"}), 400

    # Contrato financeiro: entrada + parcelas == total
    if round(down_payment + installments * installment_value, 2) != round(total_value, 2):
        return jsonify({"detail": "Entrada + parcelas deve totalizar o valor da venda (R$ %.2f)" % total_value}), 400
    if installments == 0 and round(down_payment, 2) != round(total_value, 2):
        return jsonify({"detail": "Venda a vista: entrada deve ser o valor total (R$ %.2f)" % total_value}), 400

    raw_due = data.get("installments_due") or []
    if installments > 0:
        if not isinstance(raw_due, list) or len(raw_due) != installments:
            return jsonify({"detail": "Informe um vencimento para cada parcela (%d)" % installments}), 400
        due_dates = []
        for raw in raw_due:
            d = parse_date(raw)
            if d is None:
                return jsonify({"detail": "Vencimento de parcela invalido"}), 400
            due_dates.append(d)
    else:
        due_dates = []

    # Items (produtos vendidos — detalhamento informativo)
    items = []
    for it in data.get("items") or []:
        name = (it.get("name") or "").strip()
        product_id = it.get("product_id")
        if product_id:
            prod = db.session.get(Product, product_id)
            if not prod:
                return jsonify({"detail": "Produto nao encontrado no catalogo"}), 400
            if not name:
                name = prod.name
        if not name:
            return jsonify({"detail": "Item de venda sem nome"}), 400
        try:
            qty = float(it.get("quantity") or 1)
        except (TypeError, ValueError):
            return jsonify({"detail": "Quantidade de item invalida"}), 400
        if qty <= 0:
            return jsonify({"detail": "Quantidade de item deve ser maior que zero"}), 400
        try:
            up = float(it.get("unit_price") or 0)
        except (TypeError, ValueError):
            up = 0.0
        if up < 0:
            return jsonify({"detail": "Preco unitario nao pode ser negativo"}), 400
        items.append({"product_id": product_id, "name": name, "quantity": qty, "unit_price": up})

    env_names = []
    for raw in data.get("environments") or []:
        name = (raw or "").strip()
        if name and name not in env_names:
            env_names.append(name)

    delivery_date = parse_date(data.get("delivery_date"))

    # ── Transacao unica ──
    if client.sale_concluded_at is None:
        client.sale_concluded_at = utcnow()
    if client.closed_at is None:
        client.closed_at = client.sale_concluded_at
    if deal is not None:
        if deal.sale_concluded_at is None:
            deal.sale_concluded_at = utcnow()
        if deal.closed_at is None:
            deal.closed_at = deal.sale_concluded_at

    code = _resolve_code()
    sale = Sale(
        code=code,
        client_id=client.id,
        deal_id=deal.id if deal is not None else None,
        seller_id=seller.id if seller else None,
        partner_id=partner.id if partner else None,
        lead_source=(data.get("lead_source") or "").strip(),
        sale_date=sale_date,
        total_value=total_value,
        down_payment=down_payment,
        installments=installments,
        installment_value=installment_value,
        bank_account_id=bank.id if bank else None,
        address=(data.get("address") or "").strip(),
        delivery_date=delivery_date,
        created_by=getattr(g, "current_user", None).username if getattr(g, "current_user", None) else "",
    )
    db.session.add(sale)
    db.session.flush()

    for name in env_names:
        db.session.add(SaleEnvironment(sale_id=sale.id, name=name))
    for it in items:
        db.session.add(SaleItem(sale_id=sale.id, product_id=it["product_id"],
                                name=it["name"], quantity=it["quantity"],
                                unit_price=it["unit_price"]))

    # Contas a receber: entrada + parcelas
    if down_payment > 0:
        rec = FinancialRecord(
            description=f"Entrada – Venda {code} – {client.name}",
            type="ENTRADA", category=CATEGORIA_VENDA, amount=down_payment,
            date=sale_date, status="PENDENTE", due_date=sale_date,
            client_id=client.id, bank_account_id=bank.id if bank else None,
            account_plan=PLANO_CONTA_VENDA,
        )
        db.session.add(rec)
    for i, due in enumerate(due_dates, start=1):
        rec = FinancialRecord(
            description=f"Venda {code} – parcela {i}/{len(due_dates)} – {client.name}",
            type="ENTRADA", category=CATEGORIA_VENDA, amount=installment_value,
            date=due, status="PENDENTE", due_date=due,
            client_id=client.id, bank_account_id=bank.id if bank else None,
            account_plan=PLANO_CONTA_VENDA,
        )
        db.session.add(rec)
        db.session.flush()
        db.session.add(SaleInstallment(sale_id=sale.id, due_date=due,
                                       value=installment_value, status="PENDENTE",
                                       financial_record_id=rec.id))

    # Cards de producao: um por ambiente (ou 1 generico)
    first_key, proj_funnel_id = _first_production_status()
    card_titles = [f"{name} – {client.name}" for name in env_names]
    if not card_titles:
        card_titles = [f"Projeto – {client.name}"]
    for title in card_titles:
        db.session.add(Project(
            title=title, client_id=client.id, description="",
            status=first_key, value=0, deadline=delivery_date,
            steps=STEPS_DEFAULT_PRODUCAO, funnel_id=proj_funnel_id,
            sale_id=sale.id, deal_id=deal.id if deal is not None else None,
        ))

    _log_interaction(
        client.id, "SISTEMA",
        f"Venda {code} gerada — R$ {total_value:,.2f}, {len(due_dates)} parcela(s), "
        f"{len(env_names)} ambiente(s) — contas a receber e Produção criados.",
    )

    db.session.commit()
    return jsonify(_sale_detail(sale)), 201


@bp.put("/api/sales/<sale_id>")
@token_required(roles=WRITE_ROLES)
def update_sale(sale_id):
    """Corrige a Sale (ex.: sale_date com competência errada).

    Campos editáveis: sale_date, total_value, down_payment, installments
    (+installment_value, necessário p/ validar o contrato financeiro).
    Validações básicas: sale_date válida, total > 0, entrada >= 0,
    0 <= parcelas <= 60, parcela >= 0 e entrada + N x parcela == total.
    NÃO recalcula FinancialRecords nem Projects já gerados na criação
    (trilha de auditoria do financeiro/produção) e NÃO toca no cliente.
    """
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify({"detail": "Venda nao encontrada"}), 404
    data = body_json()

    if "sale_date" in data:
        try:
            sale_date = parse_date(data.get("sale_date"))
        except (ValueError, TypeError):
            return jsonify({"detail": "sale_date invalida (formato AAAA-MM-DD)"}), 400
        if sale_date is None:
            return jsonify({"detail": "sale_date invalida (formato AAAA-MM-DD)"}), 400
        sale.sale_date = sale_date

    total = float(sale.total_value or 0)
    down = float(sale.down_payment or 0)
    inst = sale.installments or 0
    iv = float(sale.installment_value or 0)
    mexeu_financeiro = False
    if "total_value" in data:
        try:
            total = float(data.get("total_value") or 0)
        except (TypeError, ValueError):
            return jsonify({"detail": "total_value invalido"}), 400
        if total <= 0:
            return jsonify({"detail": "total_value deve ser maior que zero"}), 400
        mexeu_financeiro = True
    if "down_payment" in data:
        try:
            down = float(data.get("down_payment") or 0)
        except (TypeError, ValueError):
            return jsonify({"detail": "down_payment invalido"}), 400
        if down < 0:
            return jsonify({"detail": "down_payment nao pode ser negativo"}), 400
        mexeu_financeiro = True
    if "installments" in data:
        try:
            inst = int(data.get("installments") or 0)
        except (TypeError, ValueError):
            return jsonify({"detail": "installments invalido"}), 400
        if inst < 0 or inst > 60:
            return jsonify({"detail": "installments deve estar entre 0 e 60"}), 400
        mexeu_financeiro = True
    if "installment_value" in data:
        try:
            iv = float(data.get("installment_value") or 0)
        except (TypeError, ValueError):
            return jsonify({"detail": "installment_value invalido"}), 400
        if iv < 0:
            return jsonify({"detail": "installment_value nao pode ser negativo"}), 400
        mexeu_financeiro = True

    if mexeu_financeiro:
        if round(down + inst * iv, 2) != round(total, 2):
            return jsonify({"detail": "Entrada + parcelas deve totalizar o valor da venda (R$ %.2f)" % total}), 400
        if inst == 0 and round(down, 2) != round(total, 2):
            return jsonify({"detail": "Venda a vista: entrada deve ser o valor total (R$ %.2f)" % total}), 400
        sale.total_value = total
        sale.down_payment = down
        sale.installments = inst
        sale.installment_value = iv

    db.session.commit()
    return jsonify(_sale_detail(sale))


@bp.delete("/api/sales/<sale_id>")
@token_required(roles=WRITE_ROLES)
def delete_sale(sale_id):
    """Apaga a Sale (ambientes, itens e parcelas apagam junto por cascata).

    Se o cliente ficar sem nenhuma Sale, limpa sale_concluded_at e
    closed_at dele (volta a aparecer em `vendas_pendentes_geracao` se
    estiver fechado). NÃO mexe em funnel_status: o card permanece onde
    está no funil — a exclusão desfaz a venda gerada, não a negociação.
    Projects com sale_id são só desvinculados (sale_id NULL) e os
    FinancialRecords gerados na criação são preservados (auditoria).
    """
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify({"detail": "Venda nao encontrada"}), 404
    client = db.session.get(Client, sale.client_id) if sale.client_id else None
    deal = db.session.get(Deal, sale.deal_id) if sale.deal_id else None

    for p in list(sale.projects):
        p.sale_id = None
    db.session.delete(sale)
    db.session.flush()

    if deal is not None:
        restante_deal = db.session.query(Sale).filter_by(deal_id=deal.id).count()
        if restante_deal == 0:
            deal.sale_concluded_at = None
            deal.closed_at = None
    if client is not None:
        restante = db.session.query(Sale).filter_by(client_id=client.id).count()
        if restante == 0:
            client.sale_concluded_at = None
            client.closed_at = None
            # Legado sem deal_id: o deal principal acompanhava essas flags.
            if deal is None:
                _mirror_client_to_principal_deal(client)

    if client is not None:
        _log_interaction(
            client.id, "SISTEMA",
            f"Venda {sale.code} excluída — cliente sem Sale tem datas de "
            "conclusão limpas (funnel_status preservado).",
        )
    db.session.commit()
    return jsonify({"ok": True})