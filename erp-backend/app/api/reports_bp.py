"""GET /api/reports/* (+/export e ?format=pdf|xlsx).

Contratos replicados do FastAPI original:
- financial/clients/projects/stock/cash-flow/dre -> ReportResponse
  {title, generated_at, filters_applied, summary[], columns[], rows[]}
- dre -> tabela por periodo (mensal|trimestral|semestral|anual)
- cash-flow -> fluxo de caixa mensal (12 meses do ano)
- crm -> {periodo, negociacoes{...}, conversao{...}, ticket_medio{...},
  fluxo_caixa[], fontes_lead[]}
- lead-sources -> ReportResponse (origem dos leads: fonte/campanha, conversao e valores)
"""
import io
from datetime import date, datetime, timezone
from calendar import monthrange

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import extract, func, or_

from app.helpers import iso, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    CalendarEvent, Client, FinancialRecord, Project, ServiceTicket, StockItem, StockMovement,
)

bp = Blueprint("reports", __name__)

STATUS_LABELS_PROJECT = {
    "ORCAMENTO": "Orçamento",
    "PROJETADO": "Projetado",
    "PRODUCAO": "Produção",
    "MONTAGEM": "Montagem",
    "CONCLUIDO": "Concluído",
}


def _fmt_brl(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(value) -> str:
    if value is None:
        return "-"
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%d/%m/%Y")
        except Exception:
            return str(value)
    return str(value)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _wants_file():
    fmt = (request.args.get("format") or request.args.get("export") or "json").lower()
    return fmt if fmt in ("pdf", "xlsx") else "json"


def _send_report(report, prefix):
    fmt = _wants_file()
    if fmt == "pdf":
        return _report_pdf(report, prefix)
    if fmt == "xlsx":
        return _report_xlsx(report, prefix)
    return jsonify(report)


def _report_pdf(report, prefix):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, report.get("title", prefix))
    c.setFont("Helvetica", 10)
    y = 780
    for s in report.get("summary", []):
        c.drawString(50, y, f"{s.get('label')}: {s.get('value')}")
        y -= 16
    y -= 8
    cols = report.get("columns", [])
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, " | ".join(col.get("label", "") for col in cols)[:160])
    y -= 16
    c.setFont("Helvetica", 8)
    for row in report.get("rows", [])[:80]:
        line = " | ".join(str(row.get(col.get("key"), "")) for col in cols)[:160]
        c.drawString(50, y, line)
        y -= 12
        if y < 40:
            c.showPage()
            y = 800
            c.setFont("Helvetica", 8)
    c.showPage()
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"{prefix}.pdf")


def _report_xlsx(report, prefix):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Relatorio"
    ws.append([report.get("title", prefix)])
    for s in report.get("summary", []):
        ws.append([s.get("label"), s.get("value")])
    ws.append([])
    cols = report.get("columns", [])
    ws.append([col.get("label", "") for col in cols])
    for row in report.get("rows", []):
        ws.append([row.get(col.get("key"), "") for col in cols])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{prefix}.xlsx",
    )


# ── Financeiro ────────────────────────────────────────────────

def _build_financial():
    df = parse_date(request.args.get("date_from"))
    dt = parse_date(request.args.get("date_to"))
    ftype = request.args.get("type") or None
    category = request.args.get("category") or None
    status = request.args.get("status_filter") or request.args.get("status") or None
    project_id = request.args.get("project_id") or None

    q = db.session.query(FinancialRecord)
    if df:
        q = q.filter(FinancialRecord.date >= df)
    if dt:
        q = q.filter(FinancialRecord.date <= dt)
    if ftype:
        q = q.filter_by(type=ftype)
    if category:
        q = q.filter_by(category=category)
    if status:
        q = q.filter_by(status=status)
    if project_id:
        q = q.filter_by(project_id=project_id)
    rows = q.order_by(FinancialRecord.date.desc()).all()

    total_entrada = sum(float(r.amount or 0) for r in rows if r.type == "ENTRADA")
    total_saida = sum(float(r.amount or 0) for r in rows if r.type == "SAIDA")
    pend_entrada = sum(float(r.amount or 0) for r in rows if r.type == "ENTRADA" and r.status == "PENDENTE")
    pend_saida = sum(float(r.amount or 0) for r in rows if r.type == "SAIDA" and r.status == "PENDENTE")
    saldo = total_entrada - total_saida

    formatted = []
    for r in rows:
        proj = db.session.get(Project, r.project_id) if r.project_id else None
        formatted.append({
            "date": _fmt_date(r.date),
            "description": r.description,
            "type": "Entrada" if r.type == "ENTRADA" else "Saída",
            "category": r.category,
            "project_title": proj.title if proj else "-",
            "amount": _fmt_brl(r.amount),
            "status": "Pago" if r.status == "PAGO" else "Pendente",
        })
    return {
        "title": "Relatório Financeiro",
        "generated_at": _now_iso(),
        "filters_applied": {"date_from": iso(df), "date_to": iso(dt), "type": ftype,
                            "category": category, "status": status, "project_id": project_id},
        "summary": [
            {"label": "Total de Entradas", "value": _fmt_brl(total_entrada), "tone": "positive"},
            {"label": "Total de Saídas", "value": _fmt_brl(total_saida), "tone": "negative"},
            {"label": "Saldo do Período", "value": _fmt_brl(saldo),
             "tone": "positive" if saldo >= 0 else "negative"},
            {"label": "Pendente a Receber", "value": _fmt_brl(pend_entrada), "tone": "neutral"},
            {"label": "Pendente a Pagar", "value": _fmt_brl(pend_saida), "tone": "neutral"},
            {"label": "Quantidade de Lançamentos", "value": str(len(rows)), "tone": "neutral"},
        ],
        "columns": [
            {"key": "date", "label": "Data"},
            {"key": "description", "label": "Descrição"},
            {"key": "type", "label": "Tipo"},
            {"key": "category", "label": "Categoria"},
            {"key": "project_title", "label": "Projeto"},
            {"key": "amount", "label": "Valor"},
            {"key": "status", "label": "Status"},
        ],
        "rows": formatted,
    }


# ── Clientes ──────────────────────────────────────────────────

def _build_clients():
    cf = parse_date(request.args.get("created_from"))
    ct = parse_date(request.args.get("created_to"))
    search = (request.args.get("search") or "").strip().lower()

    rows = db.session.query(Client).order_by(Client.created_at.desc()).all()
    if cf:
        rows = [c for c in rows if c.created_at and c.created_at.date() >= cf]
    if ct:
        rows = [c for c in rows if c.created_at and c.created_at.date() <= ct]
    if search:
        rows = [c for c in rows
                if search in (c.name or "").lower()
                or search in (c.email or "").lower()
                or search in (c.cpf_cnpj or "").lower()]

    formatted = []
    for c in rows:
        projs = db.session.query(Project).filter_by(client_id=c.id).all()
        total = sum(float(p.value or 0) for p in projs)
        formatted.append({
            "name": c.name, "email": c.email or "", "phone": c.phone or "",
            "cpf_cnpj": c.cpf_cnpj or "", "address": c.address or "",
            "created_at": _fmt_date(c.created_at.date() if hasattr(c.created_at, "date") else c.created_at),
            "project_count": str(len(projs)), "total_project_value": _fmt_brl(total),
            "_nproj": len(projs), "_total": total,
        })
    com_projetos = sum(1 for r in formatted for _ in [0] if False)  # placeholder
    com_projetos = sum(1 for c in rows
                       if db.session.query(Project).filter_by(client_id=c.id).count() > 0)
    valor_total = sum(r["_total"] for r in formatted)
    for r in formatted:
        r.pop("_nproj", None)
        r.pop("_total", None)
    return {
        "title": "Relatório de Clientes",
        "generated_at": _now_iso(),
        "filters_applied": {"created_from": iso(cf), "created_to": iso(ct),
                            "search": search or None},
        "summary": [
            {"label": "Total de Clientes", "value": str(len(rows)), "tone": "neutral"},
            {"label": "Clientes com Projetos", "value": str(com_projetos), "tone": "positive"},
            {"label": "Valor Total em Projetos", "value": _fmt_brl(valor_total), "tone": "positive"},
        ],
        "columns": [
            {"key": "name", "label": "Nome"},
            {"key": "email", "label": "Email"},
            {"key": "phone", "label": "Telefone"},
            {"key": "cpf_cnpj", "label": "CPF/CNPJ"},
            {"key": "address", "label": "Endereço"},
            {"key": "created_at", "label": "Cadastrado em"},
            {"key": "project_count", "label": "Projetos"},
            {"key": "total_project_value", "label": "Valor em Projetos"},
        ],
        "rows": formatted,
    }


# ── Projetos ──────────────────────────────────────────────────

def _build_projects():
    status = request.args.get("status_filter") or request.args.get("status") or None
    client_id = request.args.get("client_id") or None
    dfrom = parse_date(request.args.get("deadline_from"))
    dto = parse_date(request.args.get("deadline_to"))

    q = db.session.query(Project)
    if status:
        q = q.filter_by(status=status)
    if client_id:
        q = q.filter_by(client_id=client_id)
    if dfrom:
        q = q.filter(Project.deadline >= dfrom)
    if dto:
        q = q.filter(Project.deadline <= dto)
    rows = q.order_by(Project.deadline).all()

    total = sum(float(p.value or 0) for p in rows)
    concluidos = sum(1 for p in rows if p.status == "CONCLUIDO")
    em_and = sum(1 for p in rows if p.status != "CONCLUIDO")
    hoje = date.today()
    atrasados = sum(1 for p in rows
                    if p.status != "CONCLUIDO" and p.deadline and p.deadline < hoje)
    formatted = [{
        "title": p.title,
        "client_name": (db.session.get(Client, p.client_id).name
                        if p.client_id and db.session.get(Client, p.client_id) else "-"),
        "status": STATUS_LABELS_PROJECT.get(p.status, p.status),
        "value": _fmt_brl(p.value),
        "deadline": _fmt_date(p.deadline),
    } for p in rows]
    return {
        "title": "Relatório de Projetos",
        "generated_at": _now_iso(),
        "filters_applied": {"status": status, "client_id": client_id,
                            "deadline_from": iso(dfrom), "deadline_to": iso(dto)},
        "summary": [
            {"label": "Total de Projetos", "value": str(len(rows)), "tone": "neutral"},
            {"label": "Valor Total dos Projetos", "value": _fmt_brl(total), "tone": "positive"},
            {"label": "Concluídos", "value": str(concluidos), "tone": "positive"},
            {"label": "Em Andamento", "value": str(em_and), "tone": "neutral"},
            {"label": "Atrasados (prazo vencido)", "value": str(atrasados),
             "tone": "negative" if atrasados else "neutral"},
        ],
        "columns": [
            {"key": "title", "label": "Projeto/Ambiente"},
            {"key": "client_name", "label": "Cliente"},
            {"key": "status", "label": "Status"},
            {"key": "value", "label": "Valor"},
            {"key": "deadline", "label": "Prazo"},
        ],
        "rows": formatted,
    }


# ── Estoque ───────────────────────────────────────────────────

def _build_stock():
    mode = request.args.get("report_mode", "items")
    if mode == "movements":
        return _build_stock_movements()
    return _build_stock_items()


def _build_stock_items():
    category_id = request.args.get("category_id") or None
    low_only = (request.args.get("low_stock_only", "false")).lower() == "true"
    q = db.session.query(StockItem)
    if category_id:
        q = q.filter_by(category_id=category_id)
    rows = q.order_by(StockItem.name).all()
    if low_only:
        rows = [i for i in rows if float(i.quantity or 0) <= float(i.min_quantity or 0)]
    total_val = sum(float(i.quantity or 0) * float(i.price or 0) for i in rows)
    below = sum(1 for i in rows if float(i.quantity or 0) <= float(i.min_quantity or 0))
    from app.models.models import Category
    formatted = []
    for i in rows:
        cat = db.session.get(Category, i.category_id) if i.category_id else None
        formatted.append({
            "name": i.name, "sku": i.sku,
            "category_name": cat.name if cat else "-",
            "quantity": f"{float(i.quantity or 0):.2f} {i.unit or ''}".strip(),
            "min_quantity": f"{float(i.min_quantity or 0):.2f} {i.unit or ''}".strip(),
            "price": _fmt_brl(i.price),
            "total_value": _fmt_brl(float(i.quantity or 0) * float(i.price or 0)),
            "supplier": i.supplier or "",
            "low_stock": "Sim" if float(i.quantity or 0) <= float(i.min_quantity or 0) else "Não",
        })
    return {
        "title": "Relatório de Estoque — Itens",
        "generated_at": _now_iso(),
        "filters_applied": {"report_mode": "items", "category_id": category_id,
                            "low_stock_only": low_only},
        "summary": [
            {"label": "Total de Itens", "value": str(len(rows)), "tone": "neutral"},
            {"label": "Valor Total em Estoque", "value": _fmt_brl(total_val), "tone": "positive"},
            {"label": "Itens Abaixo do Mínimo", "value": str(below),
             "tone": "negative" if below else "neutral"},
        ],
        "columns": [
            {"key": "name", "label": "Item"},
            {"key": "sku", "label": "SKU"},
            {"key": "category_name", "label": "Categoria"},
            {"key": "quantity", "label": "Quantidade"},
            {"key": "min_quantity", "label": "Mínimo"},
            {"key": "price", "label": "Preço Unit."},
            {"key": "total_value", "label": "Valor em Estoque"},
            {"key": "supplier", "label": "Fornecedor"},
            {"key": "low_stock", "label": "Abaixo do Mínimo"},
        ],
        "rows": formatted,
    }


def _build_stock_movements():
    mtype = request.args.get("movement_type") or None
    df = parse_date(request.args.get("date_from"))
    dt = parse_date(request.args.get("date_to"))
    category_id = request.args.get("category_id") or None

    q = db.session.query(StockMovement)
    if mtype:
        q = q.filter_by(type=mtype)
    rows = q.order_by(StockMovement.date.desc()).all()
    if df:
        rows = [m for m in rows if m.date and m.date.date() >= df]
    if dt:
        rows = [m for m in rows if m.date and m.date.date() <= dt]
    if category_id:
        rows = [m for m in rows
                if (db.session.get(StockItem, m.item_id)
                    and db.session.get(StockItem, m.item_id).category_id == category_id)]
    tot_in = sum(float(m.quantity or 0) for m in rows if m.type == "ENTRADA")
    tot_out = sum(float(m.quantity or 0) for m in rows if m.type == "SAIDA")
    formatted = []
    for m in rows:
        item = db.session.get(StockItem, m.item_id)
        dt_str = m.date.strftime("%d/%m/%Y %H:%M") if hasattr(m.date, "strftime") else str(m.date)
        formatted.append({
            "date": dt_str,
            "item_name": item.name if item else "-",
            "type": "Entrada" if m.type == "ENTRADA" else "Saída",
            "quantity": f"{float(m.quantity or 0):.2f}",
            "reason": m.reason or "",
            "created_by": m.created_by or "",
        })
    return {
        "title": "Relatório de Estoque — Movimentações",
        "generated_at": _now_iso(),
        "filters_applied": {"report_mode": "movements", "movement_type": mtype,
                            "date_from": iso(df), "date_to": iso(dt)},
        "summary": [
            {"label": "Movimentações no Período", "value": str(len(rows)), "tone": "neutral"},
            {"label": "Total Movimentado (Entradas)", "value": f"{tot_in:.2f}", "tone": "positive"},
            {"label": "Total Movimentado (Saídas)", "value": f"{tot_out:.2f}", "tone": "negative"},
        ],
        "columns": [
            {"key": "date", "label": "Data"},
            {"key": "item_name", "label": "Item"},
            {"key": "type", "label": "Tipo"},
            {"key": "quantity", "label": "Quantidade"},
            {"key": "reason", "label": "Motivo"},
            {"key": "created_by", "label": "Responsável"},
        ],
        "rows": formatted,
    }


# ── DRE ───────────────────────────────────────────────────────

MONTH_LABELS = [
    "1 - Janeiro", "2 - Fevereiro", "3 - Marco", "4 - Abril", "5 - Maio", "6 - Junho",
    "7 - Julho", "8 - Agosto", "9 - Setembro", "10 - Outubro", "11 - Novembro", "12 - Dezembro",
]


def _build_dre():
    today = date.today()
    try:
        year = int(request.args.get("year") or today.year)
    except (TypeError, ValueError):
        return jsonify({"detail": "year invalido"}), 400
    period = (request.args.get("period") or "mensal").lower()
    if period not in ("mensal", "trimestral", "semestral", "anual"):
        return jsonify({"detail": "period invalido"}), 400

    recs = db.session.query(FinancialRecord).filter(
        FinancialRecord.status == "PAGO",
        extract("year", FinancialRecord.date) == year,
    ).all()

    def bucket_of(m):
        if period == "mensal":
            return ("m", m)
        if period == "trimestral":
            return ("t", (m - 1) // 3 + 1)
        if period == "semestral":
            return ("s", 1 if m <= 6 else 2)
        return ("a", 1)

    def label_of(kind, key):
        if kind == "m":
            return MONTH_LABELS[key - 1]
        if kind == "t":
            return "%dº Trimestre" % key
        if kind == "s":
            return "%dº Semestre" % key
        return "Ano"

    def count_of(kind):
        return {"m": 12, "t": 4, "s": 2, "a": 1}[kind]

    buckets = {}
    for r in recs:
        kind, key = bucket_of(r.date.month)
        b = buckets.setdefault((kind, key), {"income": 0.0, "outcome": 0.0})
        v = float(r.amount or 0)
        if r.type == "ENTRADA":
            b["income"] += v
        else:
            b["outcome"] += v

    pend = db.session.query(FinancialRecord).filter(
        FinancialRecord.type == "ENTRADA", FinancialRecord.status == "PENDENTE",
        extract("year", FinancialRecord.date) == year,
    ).all()
    pend_income = sum(float(r.amount or 0) for r in pend)

    kind, _first = sorted(buckets)[0] if buckets else ("m", 1)
    result_rows = []
    acc = 0.0
    total_income = 0.0
    total_outcome = 0.0
    for i in range(1, count_of(kind) + 1):
        b = buckets.get((kind, i), {"income": 0.0, "outcome": 0.0})
        result = b["income"] - b["outcome"]
        acc += result
        total_income += b["income"]
        total_outcome += b["outcome"]
        result_rows.append({
            "period": label_of(kind, i),
            "income": _fmt_brl(b["income"]),
            "outcome": _fmt_brl(b["outcome"]),
            "result": _fmt_brl(result),
            "accumulated": _fmt_brl(acc),
        })

    final = total_income - total_outcome
    return {
        "title": "DRE - Demonstrativo do Resultado",
        "generated_at": _now_iso(),
        "filters_applied": {"year": year, "period": period},
        "summary": [
            {"label": "Receitas do Ano", "value": _fmt_brl(total_income), "tone": "positive"},
            {"label": "Despesas do Ano", "value": _fmt_brl(total_outcome), "tone": "negative"},
            {"label": "Resultado do Ano", "value": _fmt_brl(final),
             "tone": "positive" if final >= 0 else "negative"},
            {"label": "Faturamento Pendente", "value": _fmt_brl(pend_income), "tone": "neutral"},
        ],
        "columns": [
            {"key": "period", "label": "Período"},
            {"key": "income", "label": "Receitas"},
            {"key": "outcome", "label": "Despesas"},
            {"key": "result", "label": "Resultado"},
            {"key": "accumulated", "label": "Resultado Acumulado"},
        ],
        "rows": result_rows,
    }


# ── Fluxo de Caixa ────────────────────────────────────────────

def _build_cash_flow():
    today = date.today()
    try:
        year = int(request.args.get("year") or today.year)
    except (TypeError, ValueError):
        return jsonify({"detail": "year invalido"}), 400

    recs = db.session.query(FinancialRecord).filter(
        FinancialRecord.status == "PAGO",
        extract("year", FinancialRecord.date) == year,
    ).all()
    per_month = {}
    for r in recs:
        m = r.date.month
        b = per_month.setdefault(m, {"income": 0.0, "outcome": 0.0})
        v = float(r.amount or 0)
        if r.type == "ENTRADA":
            b["income"] += v
        else:
            b["outcome"] += v

    pend = db.session.query(FinancialRecord).filter(
        FinancialRecord.status == "PENDENTE",
        extract("year", FinancialRecord.date) == year,
    ).all()
    pend_in = sum(float(r.amount or 0) for r in pend if r.type == "ENTRADA")
    pend_out = sum(float(r.amount or 0) for r in pend if r.type == "SAIDA")

    result_rows = []
    acc = 0.0
    total_in = 0.0
    total_out = 0.0
    for i in range(1, 13):
        b = per_month.get(i, {"income": 0.0, "outcome": 0.0})
        bal = b["income"] - b["outcome"]
        acc += bal
        total_in += b["income"]
        total_out += b["outcome"]
        result_rows.append({
            "month": MONTH_LABELS[i - 1],
            "income": _fmt_brl(b["income"]),
            "outcome": _fmt_brl(b["outcome"]),
            "balance": _fmt_brl(bal),
            "accumulated": _fmt_brl(acc),
        })

    saldo = total_in - total_out
    return {
        "title": "Fluxo de Caixa Mensal",
        "generated_at": _now_iso(),
        "filters_applied": {"year": year},
        "summary": [
            {"label": "Total de Entradas", "value": _fmt_brl(total_in), "tone": "positive"},
            {"label": "Total de Saidas", "value": _fmt_brl(total_out), "tone": "negative"},
            {"label": "Saldo do Ano", "value": _fmt_brl(saldo),
             "tone": "positive" if saldo >= 0 else "negative"},
            {"label": "Pendente a Receber", "value": _fmt_brl(pend_in), "tone": "neutral"},
            {"label": "Pendente a Pagar", "value": _fmt_brl(pend_out), "tone": "neutral"},
        ],
        "columns": [
            {"key": "month", "label": "Mês"},
            {"key": "income", "label": "Entradas"},
            {"key": "outcome", "label": "Saídas"},
            {"key": "balance", "label": "Saldo do Mês"},
            {"key": "accumulated", "label": "Saldo Acumulado"},
        ],
        "rows": result_rows,
    }


# ── CRM ───────────────────────────────────────────────────────

def _build_crm():
    df = parse_date(request.args.get("date_from"))
    dt = parse_date(request.args.get("date_to"))

    clients = db.session.query(Client).all()
    if df:
        clients = [c for c in clients if c.created_at and c.created_at.date() >= df]
    if dt:
        clients = [c for c in clients if c.created_at and c.created_at.date() <= dt]

    by_stage_map = {}
    for c in clients:
        st = c.funnel_status or "PROSPECCAO"
        by_stage_map[st] = by_stage_map.get(st, 0) + 1
    by_stage = [{"funnel_status": k, "total": v} for k, v in by_stage_map.items()]

    lost = [{"name": c.name, "lost_reason": c.lost_reason,
             "created_at": iso(c.created_at)}
            for c in clients if c.funnel_status == "PERDIDO"]

    total_closed = sum(1 for c in clients if c.funnel_status == "FECHAMENTO")
    taxa = round(total_closed / len(clients) * 100, 1) if clients else 0

    concluidos = db.session.query(Project).filter_by(status="CONCLUIDO").all()
    vals = [float(p.value or 0) for p in concluidos]
    ticket = {
        "media": sum(vals) / len(vals) if vals else 0,
        "maximo": max(vals) if vals else 0,
        "minimo": min(vals) if vals else 0,
        "total_projetos": len(vals),
        "total_faturado": sum(vals),
    }

    # Fluxo de caixa: ultimos 12 meses a partir de hoje
    today = date.today()
    months = []
    ty, tm = today.year, today.month
    for _ in range(12):
        months.append((ty, tm))
        tm -= 1
        if tm == 0:
            tm, ty = 12, ty - 1
    months.reverse()
    fluxo = []
    for yy, mm in months:
        recs = db.session.query(FinancialRecord).filter(
            FinancialRecord.type == "ENTRADA", FinancialRecord.status == "PAGO",
            extract("month", FinancialRecord.date) == mm,
            extract("year", FinancialRecord.date) == yy).all()
        ds = db.session.query(FinancialRecord).filter(
            FinancialRecord.type == "SAIDA", FinancialRecord.status == "PAGO",
            extract("month", FinancialRecord.date) == mm,
            extract("year", FinancialRecord.date) == yy).all()
        r_tot = sum(float(r.amount or 0) for r in recs)
        d_tot = sum(float(r.amount or 0) for r in ds)
        fluxo.append({"mes": f"{yy:04d}-{mm:02d}", "receitas": r_tot,
                      "despesas": d_tot, "resultado": r_tot - d_tot})

    fontes_map = {}
    for c in clients:
        f = c.lead_source or "Não informado"
        fontes_map[f] = fontes_map.get(f, 0) + 1
    fontes = [{"fonte": k, "total": v}
              for k, v in sorted(fontes_map.items(), key=lambda kv: kv[1], reverse=True)]

    return {
        "periodo": {"date_from": iso(df), "date_to": iso(dt)},
        "negociacoes": {"total": len(clients), "por_etapa": by_stage,
                        "perdidas": lost, "total_perdidas": len(lost)},
        "conversao": {"total_clientes": len(clients),
                      "total_fechamentos": total_closed, "taxa": taxa},
        "ticket_medio": ticket,
        "fluxo_caixa": fluxo,
        "fontes_lead": fontes,
    }


# ── Origem dos Leads ──────────────────────────────────────────

def _build_lead_sources():
    df = parse_date(request.args.get("date_from"))
    dt = parse_date(request.args.get("date_to"))
    group_by = (request.args.get("group_by") or "source").lower()
    if group_by not in ("source", "campaign"):
        group_by = "source"
    clients = db.session.query(Client).all()
    if df:
        clients = [c for c in clients if c.created_at and c.created_at.date() >= df]
    if dt:
        clients = [c for c in clients if c.created_at and c.created_at.date() <= dt]
    groups = {}
    for c in clients:
        key = (c.lead_source or "Não informado") if group_by == "source" else (c.campaign or "Sem campanha")
        g = groups.setdefault(key, {"leads": 0, "ativos": 0, "fechados": 0, "perdidos": 0, "valor_estimado": 0.0, "valor_projetos": 0.0})
        g["leads"] += 1
        if c.funnel_status != "PERDIDO":
            g["ativos"] += 1
        if c.funnel_status == "FECHAMENTO":
            g["fechados"] += 1
        if c.funnel_status == "PERDIDO":
            g["perdidos"] += 1
        g["valor_estimado"] += float(c.negotiation_value or 0) or float(c.estimated_value or 0)
        for p in c.projects:
            if p.status != "CONCLUIDO":
                g["valor_projetos"] += float(p.value or 0)
    ordered = sorted(groups.items(), key=lambda kv: kv[1]["leads"], reverse=True)
    total_leads = sum(g["leads"] for _, g in ordered)
    total_fechados = sum(g["fechados"] for _, g in ordered)
    total_estimado = sum(g["valor_estimado"] for _, g in ordered)
    total_projetos = sum(g["valor_projetos"] for _, g in ordered)
    group_label = "Fonte" if group_by == "source" else "Campanha"
    columns = [
        {"key": "group", "label": group_label},
        {"key": "leads", "label": "Leads"},
        {"key": "ativos", "label": "Ativos"},
        {"key": "fechados", "label": "Fechados"},
        {"key": "perdidos", "label": "Perdidos"},
        {"key": "taxa", "label": "Conversão"},
        {"key": "valor_estimado", "label": "Valor Estimado"},
        {"key": "valor_projetos", "label": "Valor em Projetos"},
    ]
    rows = []
    for name, g in ordered:
        taxa = (g["fechados"] / g["leads"] * 100) if g["leads"] else 0.0
        rows.append({
            "group": name,
            "leads": str(g["leads"]),
            "ativos": str(g["ativos"]),
            "fechados": str(g["fechados"]),
            "perdidos": str(g["perdidos"]),
            "taxa": (("%.1f" % taxa).replace(".", ",")) + "%",
            "valor_estimado": _fmt_brl(g["valor_estimado"]),
            "valor_projetos": _fmt_brl(g["valor_projetos"]),
        })
    taxa_geral = (total_fechados / total_leads * 100) if total_leads else 0.0
    return {
        "title": "Relatório de Origem dos Leads",
        "generated_at": _now_iso(),
        "filters_applied": {"date_from": iso(df), "date_to": iso(dt), "group_by": group_by},
        "summary": [
            {"label": "Total de Leads", "value": str(total_leads), "tone": "neutral"},
            {"label": "Leads Fechados", "value": str(total_fechados), "tone": "positive"},
            {"label": "Taxa de Conversão", "value": (("%.1f" % taxa_geral).replace(".", ",")) + "%", "tone": "positive" if taxa_geral >= 50 else "neutral"},
            {"label": "Valor Estimado Total", "value": _fmt_brl(total_estimado), "tone": "neutral"},
            {"label": "Valor em Projetos", "value": _fmt_brl(total_projetos), "tone": "positive"},
        ],
        "columns": columns,
        "rows": rows,
    }


# ── Pós-venda (Tickets) ───────────────────────────────────────

def _build_tickets():
    from collections import Counter

    VALID_TICKET_STATUSES = ["ABERTO", "EM_ANALISE", "AGENDADO", "EM_ATENDIMENTO", "RESOLVIDO", "ENCERRADO"]

    status_filter = (request.args.get("status") or "").strip().upper() or None
    client_id = (request.args.get("client_id") or "").strip() or None
    df = parse_date(request.args.get("date_from"))
    dt = parse_date(request.args.get("date_to"))
    in_warranty_raw = request.args.get("in_warranty")
    in_warranty = None
    if in_warranty_raw is not None and str(in_warranty_raw).strip() != "":
        low = str(in_warranty_raw).strip().lower()
        if low in ("true", "1", "sim", "yes"):
            in_warranty = True
        elif low in ("false", "0", "nao", "não", "no"):
            in_warranty = False
        else:
            in_warranty = None

    rows = db.session.query(ServiceTicket).all()
    # aplica filtros em python (similar a _build_lead_sources)
    if status_filter:
        rows = [t for t in rows if (t.status or "").upper() == status_filter]
    if client_id:
        rows = [t for t in rows if t.client_id == client_id]
    if df:
        rows = [t for t in rows if t.opened_at and t.opened_at.date() >= df]
    if dt:
        rows = [t for t in rows if t.opened_at and t.opened_at.date() <= dt]
    if in_warranty is not None:
        rows = [t for t in rows if t.in_warranty is in_warranty]

    total = len(rows)
    por_status = Counter((t.status or "").upper() for t in rows)
    custo_total = sum(float(t.cost or 0) for t in rows)
    custo_medio = (custo_total / total) if total else 0
    dentro_garantia = sum(1 for t in rows if t.in_warranty is True)
    fora_garantia = sum(1 for t in rows if t.in_warranty is False)

    # tempo medio de resolucao
    tempos = []
    for t in rows:
        if t.resolved_at and t.opened_at:
            try:
                delta = t.resolved_at - t.opened_at
                dias = delta.total_seconds() / 86400
                tempos.append(dias)
            except Exception:
                continue
    tempo_medio = (sum(tempos) / len(tempos)) if tempos else None

    # causa mais frequente por status
    causa_by_status = {}
    for st in VALID_TICKET_STATUSES:
        filtered = [t for t in rows if (t.status or "").upper() == st]
        if not filtered:
            continue
        c_counter = Counter(((t.cause or "").strip() or "Não informado") for t in filtered)
        # pega mais comum que nao seja vazio, mas se todos forem "Não informado" mantém
        most, _ = c_counter.most_common(1)[0]
        causa_by_status[st] = most

    # causa geral top (para referencia)
    causa_counts = Counter(((t.cause or "").strip() or "Não informado") for t in rows)

    # monta summary
    em_atendimento_qtd = por_status.get("AGENDADO", 0) + por_status.get("EM_ATENDIMENTO", 0)
    summary = [
        {"label": "Total de Chamados", "value": str(total), "tone": "neutral"},
        {"label": "Abertos", "value": str(por_status.get("ABERTO", 0)), "tone": "neutral"},
        {"label": "Em Atendimento", "value": str(em_atendimento_qtd), "tone": "neutral"},
        {"label": "Resolvidos", "value": str(por_status.get("RESOLVIDO", 0)), "tone": "positive"},
        {"label": "Encerrados", "value": str(por_status.get("ENCERRADO", 0)), "tone": "neutral"},
        {"label": "Custo Total", "value": _fmt_brl(custo_total), "tone": "negative" if custo_total > 0 else "neutral"},
        {"label": "Custo Médio", "value": _fmt_brl(custo_medio), "tone": "neutral"},
        {"label": "Dentro da Garantia", "value": str(dentro_garantia), "tone": "positive"},
        {"label": "Fora da Garantia", "value": str(fora_garantia), "tone": "negative"},
        {"label": "Tempo Médio de Resolução", "value": f"{tempo_medio:.1f} dias" if tempo_medio is not None else "-", "tone": "neutral"},
    ]

    columns = [
        {"key": "status", "label": "Status"},
        {"key": "count", "label": "Qtd"},
        {"key": "percentual", "label": "Percentual"},
        {"key": "custo", "label": "Custo"},
        {"key": "causa", "label": "Causa Mais Frequente"},
    ]

    rows_out = []
    for st in VALID_TICKET_STATUSES:
        cnt = por_status.get(st, 0)
        if cnt == 0 and total > 0:
            # só inclui status com ocorrências quando há dados; se total==0 inclui vazio?
            continue
        if total == 0:
            # sem dados: cria linhas vazias? melhor não criar nenhuma
            continue
        pct = (cnt / total * 100) if total else 0
        custo_status = sum(float(t.cost or 0) for t in rows if (t.status or "").upper() == st)
        causa = causa_by_status.get(st, "-")
        rows_out.append({
            "status": st,
            "count": str(cnt),
            "percentual": f"{pct:.1f}%".replace(".", ","),
            "custo": _fmt_brl(custo_status),
            "causa": causa,
        })

    # Se não houver agregação (ex: filtro status específico), mas ainda houver rows,
    # garantir que causa Dobradiça/descricao apareça: já coberto por causa_by_status.
    # Fallback: se rows_out vazio mas total>0 (status filtrado desconhecido), criar linhas por ticket
    if not rows_out and total > 0:
        for t in rows:
            rows_out.append({
                "status": t.status or "-",
                "count": "1",
                "percentual": "100,0%",
                "custo": _fmt_brl(t.cost),
                "causa": (t.cause or "").strip() or t.description or "-",
            })

    return {
        "title": "Relatório de Pós-venda - Chamados",
        "generated_at": _now_iso(),
        "filters_applied": {
            "status": status_filter,
            "client_id": client_id,
            "date_from": iso(df),
            "date_to": iso(dt),
            "in_warranty": in_warranty,
        },
        "summary": summary,
        "columns": columns,
        "rows": rows_out,
    }


_BUILDERS = {
    "financial": (_build_financial, "relatorio-financeiro"),
    "cash-flow": (_build_cash_flow, "fluxo-caixa-mensal"),
    "dre": (_build_dre, "relatorio-dre"),
    "clients": (_build_clients, "relatorio-clientes"),
    "projects": (_build_projects, "relatorio-projetos"),
    "stock": (_build_stock, "relatorio-estoque"),
    "lead-sources": (_build_lead_sources, "relatorio-leads-fontes"),
    "tickets": (_build_tickets, "relatorio-tickets"),
}


def _serve(name):
    builder, prefix = _BUILDERS[name]
    return _send_report(builder(), prefix)


@bp.get("/api/reports/financial")
@token_required()
def r_financial():
    return _serve("financial")


@bp.get("/api/reports/financial/export")
@token_required()
def r_financial_export():
    return _serve("financial")


@bp.get("/api/reports/clients")
@token_required()
def r_clients():
    return _serve("clients")


@bp.get("/api/reports/clients/export")
@token_required()
def r_clients_export():
    return _serve("clients")


@bp.get("/api/reports/projects")
@token_required()
def r_projects():
    return _serve("projects")


@bp.get("/api/reports/projects/export")
@token_required()
def r_projects_export():
    return _serve("projects")


@bp.get("/api/reports/stock")
@token_required()
def r_stock():
    return _serve("stock")


@bp.get("/api/reports/stock/export")
@token_required()
def r_stock_export():
    return _serve("stock")


@bp.get("/api/reports/dre")
@token_required()
def r_dre():
    return _serve("dre")


@bp.get("/api/reports/crm")
@token_required()
def r_crm():
    return jsonify(_build_crm())


@bp.get("/api/reports/lead-sources")
@token_required()
def r_lead_sources():
    return _serve("lead-sources")


@bp.get("/api/reports/lead-sources/export")
@token_required()
def r_lead_sources_export():
    return _serve("lead-sources")


@bp.get("/api/reports/cash-flow")
@token_required()
def r_cash_flow():
    return _serve("cash-flow")


@bp.get("/api/reports/cash-flow/export")
@token_required()
def r_cash_flow_export():
    return _serve("cash-flow")


@bp.get("/api/reports/tickets")
@token_required()
def r_tickets():
    return _serve("tickets")


@bp.get("/api/reports/tickets/export")
@token_required()
def r_tickets_export():
    return _serve("tickets")
