"""CRUD /api/financial, /upcoming, /overdue, /<id>/receipt e /recurring."""
import io
from datetime import date, timedelta

from flask import Blueprint, jsonify, request, send_file

from app.helpers import body_json, iso, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import BankAccount, FinancialRecord, RecurringFinancial, Supplier

bp = Blueprint("financial", __name__)

FIN_FIELDS = (
    "description", "type", "category", "amount", "date", "project_id", "status", "due_date",
    "doc_number", "issue_date", "doc_type", "bank", "account_plan", "item_description",
    "installments", "client_id", "supplier_id", "is_recurring", "bank_account_id",
)

FREQ_DAYS = {"SEMANAL": 7, "QUINZENAL": 15, "MENSAL": 30, "ANUAL": 365}

DOC_TYPES = ("BOLETO", "CHEQUE", "DEBITO_AUTOMATICO", "DINHEIRO", "FATURA", "PIX")


def _validate_fin(data):
    v = data.get("doc_type")
    if v not in (None, "") and v not in DOC_TYPES:
        return jsonify({"detail": "doc_type invalido"}), 400
    if "installments" in data:
        try:
            n = int(data["installments"])
        except (TypeError, ValueError):
            return jsonify({"detail": "installments invalido"}), 400
        if n < 1:
            return jsonify({"detail": "installments deve ser maior ou igual a 1"}), 400
    if "bank_account_id" in data and data.get("bank_account_id") not in (None, ""):
        raw = data.get("bank_account_id")
        bid = str(raw).strip() if isinstance(raw, str) else str(raw).strip()
        if bid:
            acc = db.session.get(BankAccount, bid)
            if not acc:
                return jsonify({"detail": "Conta bancaria nao encontrada: bank_account_id invalido"}), 404
    return None


def _enrich(rec):
    """to_dict + client_name/project_title via relacionamentos."""
    from app.models.models import Client, Project

    d = rec.to_dict()
    project = db.session.get(Project, rec.project_id) if rec.project_id else None
    d["project_title"] = project.title if project else None
    client = db.session.get(Client, project.client_id) if project and project.client_id else None
    d["client_id"] = client.id if client else None
    d["client_name"] = client.name if client else None
    supplier = db.session.get(Supplier, rec.supplier_id) if rec.supplier_id else None
    d["supplier_name"] = supplier.name if supplier else None
    return d


def _apply(data, rec):
    for f in FIN_FIELDS:
        if f not in data:
            continue
        v = data[f]
        if f in ("date", "due_date", "issue_date"):
            v = parse_date(v)
        if f in ("project_id", "client_id", "supplier_id", "bank_account_id") and v == "":
            v = None
        if f == "bank_account_id":
            if v is None or v == "":
                v = None
            else:
                # keep as string id, trim
                if isinstance(v, str):
                    v = v.strip()
                    if v == "":
                        v = None
                else:
                    # if not string (e.g. None handled, otherwise convert)
                    try:
                        v = str(v).strip()
                        if v == "":
                            v = None
                    except Exception:
                        v = None
            setattr(rec, f, v)
            continue
        if f == "installments":
            try:
                v = int(v)
            except (TypeError, ValueError):
                v = 1
        if f == "is_recurring":
            v = bool(v)
        setattr(rec, f, v)


# ── Lancamentos ───────────────────────────────────────────────

@bp.get("/api/financial/upcoming")
@token_required()
def upcoming():
    """Lancamentos PENDENTES com vencimento nos proximos N dias (default 7).

    Contrato original (FastAPI): retorna dict com receivables/payables
    separados, totais e days. Frontend UpcomingPaymentsCard depende disso.
    """
    try:
        days = int(request.args.get("days") or 7)
    except (TypeError, ValueError):
        days = 7
    days = max(1, min(days, 365))
    today = date.today()
    limit = today + timedelta(days=days)
    rows = (
        db.session.query(FinancialRecord)
        .filter(
            FinancialRecord.status == "PENDENTE",
            FinancialRecord.due_date.isnot(None),
            FinancialRecord.due_date >= today,
            FinancialRecord.due_date <= limit,
        )
        .order_by(FinancialRecord.due_date)
        .all()
    )
    result = [_enrich(r) for r in rows]
    receivables = [r for r in result if r["type"] == "ENTRADA"]
    payables = [r for r in result if r["type"] == "SAIDA"]
    return jsonify(
        {
            "receivables": receivables,
            "payables": payables,
            "total_receivables": sum(float(r["amount"] or 0) for r in receivables),
            "total_payables": sum(float(r["amount"] or 0) for r in payables),
            "days": days,
        }
    )


@bp.get("/api/financial/overdue")
@token_required()
def overdue():
    """ENTRADA + PENDENTE com date vencida, agrupado por cliente/projeto.

    Contrato original: {clients: [{client_id, client_name, total_overdue,
    projects: [{project_id, project_title, subtotal, records: [...]}}],
    grand_total}. Frontend FinancialView (aba pendencias) depende disso.
    """
    today = date.today()
    rows = (
        db.session.query(FinancialRecord)
        .filter(
            FinancialRecord.type == "ENTRADA",
            FinancialRecord.status == "PENDENTE",
            FinancialRecord.date.isnot(None),
            FinancialRecord.date < today,
        )
        .order_by(FinancialRecord.date)
        .all()
    )
    clients_map = {}
    for rec in rows:
        d = _enrich(rec)
        client_id = d.get("client_id") or "__sem_cliente__"
        if client_id not in clients_map:
            clients_map[client_id] = {
                "client_id": d.get("client_id"),
                "client_name": d.get("client_name") or "Sem cliente vinculado",
                "total_overdue": 0.0,
                "projects": {},
            }
        project_id = d.get("project_id") or "__sem_projeto__"
        bucket = clients_map[client_id]["projects"]
        if project_id not in bucket:
            bucket[project_id] = {
                "project_id": d.get("project_id"),
                "project_title": d.get("project_title") or "Sem projeto vinculado",
                "subtotal": 0.0,
                "records": [],
            }
        amount = float(d["amount"] or 0)
        clients_map[client_id]["total_overdue"] += amount
        bucket[project_id]["subtotal"] += amount
        bucket[project_id]["records"].append(
            {"id": d["id"], "description": d["description"], "amount": amount, "date": d["date"]}
        )
    clients_list = []
    for c in clients_map.values():
        c["projects"] = list(c["projects"].values())
        clients_list.append(c)
    clients_list.sort(key=lambda c: c["total_overdue"], reverse=True)
    return jsonify({"clients": clients_list, "grand_total": sum(c["total_overdue"] for c in clients_list)})


@bp.get("/api/financial")
@token_required()
def list_records():
    """Lista lancamentos com filtros server-side (opcionais, combinaveis).

    type=ENTRADA|SAIDA, status=PAGO|PENDENTE, due_from=YYYY-MM-DD,
    due_to=YYYY-MM-DD, overdue=1 (vencidas e ainda em aberto).
    Parametro invalido devolve 400 — parse_date levanta ValueError, entao
    sem tratamento viraria 500.
    """
    q = db.session.query(FinancialRecord)

    tipo = (request.args.get("type") or "").upper()
    if tipo:
        if tipo not in ("ENTRADA", "SAIDA"):
            return jsonify({"detail": "type deve ser ENTRADA ou SAIDA"}), 400
        q = q.filter(FinancialRecord.type == tipo)

    status = (request.args.get("status") or "").upper()
    if status:
        if status not in ("PAGO", "PENDENTE"):
            return jsonify({"detail": "status deve ser PAGO ou PENDENTE"}), 400
        q = q.filter(FinancialRecord.status == status)

    try:
        due_from = parse_date(request.args.get("due_from"))
        due_to = parse_date(request.args.get("due_to"))
    except ValueError:
        return jsonify({"detail": "due_from/due_to devem estar em YYYY-MM-DD"}), 400
    if due_from:
        q = q.filter(FinancialRecord.due_date >= due_from)
    if due_to:
        q = q.filter(FinancialRecord.due_date <= due_to)

    if (request.args.get("overdue") or "").lower() in ("1", "true", "sim"):
        q = q.filter(
            FinancialRecord.status == "PENDENTE",
            FinancialRecord.due_date < date.today(),
        )

    rows = q.order_by(FinancialRecord.date.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@bp.get("/api/financial/aging")
@token_required()
def aging():
    """Aging das contas em ABERTO por vencimento, para um tipo.

    ENTrada = a receber, SAIDA = a pagar. Buckets: vencidas, 0-7 dias,
    8-30 dias e mais de 30 dias. Lancamento sem vencimento nao entra em
    bucket nenhum — vai em `no_due_date`, para o total nao mentir.
    """
    tipo = (request.args.get("type") or "SAIDA").upper()
    if tipo not in ("ENTRADA", "SAIDA"):
        return jsonify({"detail": "type deve ser ENTRADA ou SAIDA"}), 400

    rows = db.session.query(FinancialRecord).filter(
        FinancialRecord.type == tipo,
        FinancialRecord.status == "PENDENTE",
    ).all()

    hoje = date.today()
    buckets = {
        "vencidas": {"count": 0, "total": 0.0},
        "0_7": {"count": 0, "total": 0.0},
        "8_30": {"count": 0, "total": 0.0},
        "acima_30": {"count": 0, "total": 0.0},
    }
    sem_data = {"count": 0, "total": 0.0}
    total_geral = 0.0

    for r in rows:
        valor = float(r.amount or 0)
        total_geral += valor
        if r.due_date is None:
            sem_data["count"] += 1
            sem_data["total"] += valor
            continue
        dias = (hoje - r.due_date).days
        if dias > 0:
            chave = "vencidas"
        elif dias >= -7:
            chave = "0_7"
        elif dias >= -30:
            chave = "8_30"
        else:
            chave = "acima_30"
        buckets[chave]["count"] += 1
        buckets[chave]["total"] += valor

    return jsonify({
        "type": tipo,
        "reference_date": hoje.isoformat(),
        "open_count": len(rows),
        "open_total": round(total_geral, 2),
        "buckets": {
            k: {"count": v["count"], "total": round(v["total"], 2)}
            for k, v in buckets.items()
        },
        "no_due_date": {"count": sem_data["count"], "total": round(sem_data["total"], 2)},
    })


@bp.post("/api/financial")
@token_required()
def create_record():
    data = body_json()
    if not (data.get("description") or "").strip():
        return jsonify({"detail": "description e obrigatoria"}), 400
    if data.get("type") not in ("ENTRADA", "SAIDA"):
        return jsonify({"detail": "type deve ser ENTRADA ou SAIDA"}), 400
    if data.get("amount") is None:
        return jsonify({"detail": "amount e obrigatorio"}), 400
    err = _validate_fin(data)
    if err:
        return err
    rec = FinancialRecord(
        description=data["description"].strip(),
        type=data["type"],
        category=data.get("category") or "",
        amount=data.get("amount") or 0,
        date=parse_date(data.get("date")) or date.today(),
        project_id=data.get("project_id") or None,
        status=data.get("status") or "PENDENTE",
        due_date=parse_date(data.get("due_date")),
    )
    _apply(data, rec)
    if rec.due_date is None:
        rec.due_date = rec.date
    if rec.status not in ("PAGO", "PENDENTE"):
        return jsonify({"detail": "status deve ser PAGO ou PENDENTE"}), 400
    db.session.add(rec)
    db.session.commit()
    return jsonify(_enrich(rec)), 201


@bp.put("/api/financial/<record_id>")
@token_required()
def update_record(record_id):
    rec = db.session.get(FinancialRecord, record_id)
    if not rec:
        return jsonify({"detail": "Lancamento nao encontrado"}), 404
    data = body_json()
    if "type" in data and data["type"] not in ("ENTRADA", "SAIDA"):
        return jsonify({"detail": "type deve ser ENTRADA ou SAIDA"}), 400
    if "status" in data and data["status"] not in ("PAGO", "PENDENTE"):
        return jsonify({"detail": "status deve ser PAGO ou PENDENTE"}), 400
    err = _validate_fin(data)
    if err:
        return err
    _apply(data, rec)
    db.session.commit()
    return jsonify(rec.to_dict())


@bp.delete("/api/financial/<record_id>")
@token_required()
def delete_record(record_id):
    rec = db.session.get(FinancialRecord, record_id)
    if not rec:
        return jsonify({"detail": "Lancamento nao encontrado"}), 404
    db.session.delete(rec)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/financial/<record_id>/receipt")
@token_required()
def receipt(record_id):
    rec = db.session.get(FinancialRecord, record_id)
    if not rec:
        return jsonify({"detail": "Lancamento nao encontrado"}), 404
    fmt = (request.args.get("format") or "json").lower()
    if fmt == "pdf":
        return _receipt_pdf(rec)
    if fmt == "docx":
        return _receipt_docx(rec)
    return jsonify({"receipt": rec.to_dict()})


def _receipt_pdf(rec):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, 780, "EME Moveis - Recibo Financeiro")
    c.setFont("Helvetica", 12)
    lines = [
        f"Descricao: {rec.description}",
        f"Tipo: {rec.type}",
        f"Categoria: {rec.category or '-'}",
        f"Valor: R$ {num(rec.amount):.2f}",
        f"Data: {iso(rec.date)}",
        f"Vencimento: {iso(rec.due_date) or '-'}",
        f"Status: {rec.status}",
    ]
    y = 740
    for line in lines:
        c.drawString(60, y, line)
        y -= 24
    c.showPage()
    c.save()
    buf.seek(0)
    return send_file(
        buf, mimetype="application/pdf", as_attachment=True, download_name=f"recibo-{rec.id}.pdf"
    )


def _receipt_docx(rec):
    from docx import Document

    doc = Document()
    doc.add_heading("EME Moveis - Recibo Financeiro", level=1)
    doc.add_paragraph(f"Descricao: {rec.description}")
    doc.add_paragraph(f"Tipo: {rec.type}")
    doc.add_paragraph(f"Categoria: {rec.category or '-'}")
    doc.add_paragraph(f"Valor: R$ {num(rec.amount):.2f}")
    doc.add_paragraph(f"Data: {iso(rec.date)}")
    doc.add_paragraph(f"Vencimento: {iso(rec.due_date) or '-'}")
    doc.add_paragraph(f"Status: {rec.status}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"recibo-{rec.id}.docx",
    )


# ── Recorrentes ───────────────────────────────────────────────

@bp.get("/api/financial/recurring")
@token_required()
def list_recurring():
    rows = db.session.query(RecurringFinancial).order_by(RecurringFinancial.next_date).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/financial/recurring")
@token_required()
def create_recurring():
    data = body_json()
    # Compat: FinancialCreateExtended usa `mode`/`installments`/`frequency`
    if data.get("mode") == "PARCELADO" and data.get("installments"):
        return _create_installments(data)
    for req in ("description", "type", "amount", "frequency"):
        if data.get(req) is None or data.get(req) == "":
            return jsonify({"detail": f"{req} e obrigatorio"}), 400
    if data["type"] not in ("ENTRADA", "SAIDA"):
        return jsonify({"detail": "type deve ser ENTRADA ou SAIDA"}), 400
    if data["frequency"] not in FREQ_DAYS:
        return jsonify({"detail": "frequency invalida"}), 400
    start = parse_date(data.get("start_date")) or parse_date(data.get("date")) or date.today()
    rec = RecurringFinancial(
        description=data["description"],
        type=data["type"],
        category=data.get("category") or "",
        amount=data.get("amount") or 0,
        frequency=data["frequency"],
        start_date=start,
        next_date=parse_date(data.get("next_date")) or start,
        project_id=data.get("project_id") or None,
        active=True,
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify(rec.to_dict()), 201


def _create_installments(data):
    try:
        n = int(data.get("installments") or 0)
    except (TypeError, ValueError):
        return jsonify({"detail": "installments invalido"}), 400
    if n < 2 or n > 60:
        return jsonify({"detail": "installments deve estar entre 2 e 60"}), 400
    base = parse_date(data.get("date")) or date.today()
    total = float(data.get("amount") or 0)
    per = round(total / n, 2)
    created = []
    for i in range(n):
        due = base + timedelta(days=30 * i)
        rec = FinancialRecord(
            description=f"{data.get('description')} ({i + 1}/{n})",
            type=data.get("type"),
            category=data.get("category") or "",
            amount=per,
            date=due,
            project_id=data.get("project_id") or None,
            status=data.get("status") or "PENDENTE",
            due_date=due,
        )
        db.session.add(rec)
        created.append(rec)
    db.session.commit()
    return jsonify({"ok": True, "installments": [r.to_dict() for r in created]}), 201


@bp.delete("/api/financial/recurring/<rec_id>")
@token_required()
def delete_recurring(rec_id):
    rec = db.session.get(RecurringFinancial, rec_id)
    if not rec:
        return jsonify({"detail": "Recorrencia nao encontrada"}), 404
    rec.active = False
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/financial/recurring/process-due")
@token_required()
def process_due():
    today = date.today()
    due = (
        db.session.query(RecurringFinancial)
        .filter(RecurringFinancial.active.is_(True), RecurringFinancial.next_date <= today)
        .all()
    )
    generated = []
    for rec in due:
        fin = FinancialRecord(
            description=rec.description,
            type=rec.type,
            category=rec.category,
            amount=rec.amount,
            date=today,
            project_id=rec.project_id,
            status="PENDENTE",
            due_date=today,
        )
        db.session.add(fin)
        rec.next_date = rec.next_date + timedelta(days=FREQ_DAYS.get(rec.frequency, 30))
        generated.append(fin)
    db.session.commit()
    return jsonify({"ok": True, "processed": len(generated)})
