"""CRUD /api/tickets + fotos (multipart) + agenda automatica ASSISTENCIA."""
import os
import uuid
from datetime import date, datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.auth import token_required
from app.extensions import db
from app.helpers import body_json, iso, num, parse_date
from app.models.models import CalendarEvent, Client, Project, ServiceTicket, TicketPhoto, User

bp = Blueprint("tickets", __name__)

VALID_STATUSES = {"ABERTO", "EM_ANALISE", "AGENDADO", "EM_ATENDIMENTO", "RESOLVIDO", "ENCERRADO"}


def _upload_dir():
    d = current_app.config["UPLOAD_DIR"]
    os.makedirs(d, exist_ok=True)
    return d


def _creator():
    return g.current_user.username if hasattr(g, "current_user") else ""


def _next_ticket_number():
    prefix = f"CH-{date.today().year}-"
    row = (
        db.session.query(ServiceTicket)
        .filter(ServiceTicket.number.like(f"{prefix}%"))
        .order_by(ServiceTicket.number.desc())
        .first()
    )
    if row and row.number:
        try:
            suffix = row.number.split("-")[-1]
            n = int(suffix)
        except Exception:
            n = 0
        nxt = n + 1
    else:
        nxt = 1
    return f"{prefix}{nxt:04d}"


def _ensure_calendar_event(ticket):
    """Create or update CalendarEvent ASSISTENCIA for AGENDADO tickets.

    Deduplica por ticket.calendar_event_id - nao cria duplicado.
    """
    if ticket.status != "AGENDADO" or not ticket.scheduled_at:
        return
    if ticket.calendar_event_id:
        # atualiza evento existente
        ev = db.session.get(CalendarEvent, ticket.calendar_event_id)
        if ev:
            ev.title = f"Assistencia {ticket.number}: {ticket.description[:50]}"
            ev.start_date = ticket.scheduled_at
            ev.client_id = ticket.client_id
            ev.project_id = ticket.project_id
            ev.assigned_user_id = ticket.assigned_user_id
            ev.description = f"Chamado {ticket.number} - {ticket.description[:100]}"
            ev.type = "ASSISTENCIA"
            ev.status = "AGENDADO"
        return
    # cria novo
    ev = CalendarEvent(
        title=f"Assistencia {ticket.number}: {ticket.description[:50]}",
        description=f"Chamado {ticket.number} - {ticket.description[:100]}",
        type="ASSISTENCIA",
        status="AGENDADO",
        start_date=ticket.scheduled_at,
        client_id=ticket.client_id,
        project_id=ticket.project_id,
        assigned_user_id=ticket.assigned_user_id,
    )
    db.session.add(ev)
    db.session.flush()
    ticket.calendar_event_id = ev.id


def _enrich(ticket):
    d = ticket.to_dict()
    d["photos"] = [p.to_dict() for p in ticket.photos]
    return d


# ── LIST ──────────────────────────────────────────────────────────


@bp.get("/api/tickets")
@token_required()
def list_tickets():
    q = db.session.query(ServiceTicket)
    status = request.args.get("status")
    client_id = request.args.get("client_id")
    if status:
        q = q.filter(ServiceTicket.status == status)
    if client_id:
        q = q.filter(ServiceTicket.client_id == client_id)
    rows = q.order_by(ServiceTicket.opened_at.desc()).all()
    return jsonify([_enrich(r) for r in rows])


# ── CREATE ────────────────────────────────────────────────────────


@bp.post("/api/tickets")
@token_required()
def create_ticket():
    data = body_json()

    # client_id obrigatorio
    client_id = data.get("client_id")
    if not client_id or (isinstance(client_id, str) and not client_id.strip()):
        return jsonify({"detail": "client_id e obrigatorio"}), 400
    if not db.session.get(Client, client_id):
        return jsonify({"detail": "Cliente nao encontrado"}), 404

    # project_id opcional
    project_id = data.get("project_id")
    if project_id not in (None, ""):
        if not db.session.get(Project, project_id):
            return jsonify({"detail": "Projeto nao encontrado"}), 404
    else:
        project_id = None

    # description obrigatoria
    raw_desc = data.get("description")
    if not isinstance(raw_desc, str) or not raw_desc.strip():
        return jsonify({"detail": "description e obrigatoria"}), 400
    description = raw_desc.strip()

    # assigned_user_id opcional
    assigned_user_id = data.get("assigned_user_id")
    if assigned_user_id not in (None, ""):
        if not db.session.get(User, assigned_user_id):
            return jsonify({"detail": "Usuario nao encontrado"}), 404
    else:
        assigned_user_id = None

    # status
    raw_status = data.get("status")
    if raw_status is None or (isinstance(raw_status, str) and not raw_status.strip()):
        status = "ABERTO"
    else:
        status = str(raw_status).strip().upper()
        if status not in VALID_STATUSES:
            return jsonify({"detail": "status invalido"}), 400

    # cost
    cost_val = data.get("cost")
    if cost_val is not None and cost_val != "":
        try:
            c = float(cost_val)
        except (TypeError, ValueError):
            return jsonify({"detail": "cost invalido"}), 400
        if c < 0:
            return jsonify({"detail": "cost deve ser maior ou igual a zero"}), 400
        # check nan/inf
        import math
        if math.isnan(c) or math.isinf(c):
            return jsonify({"detail": "cost invalido"}), 400
        cost = c
    else:
        cost = 0

    # scheduled_at
    scheduled_at = None
    if data.get("scheduled_at") not in (None, ""):
        try:
            scheduled_at = parse_date(data.get("scheduled_at"))
        except Exception:
            return jsonify({"detail": "scheduled_at invalida"}), 400
        if scheduled_at is None:
            return jsonify({"detail": "scheduled_at invalida"}), 400

    # notes
    notes = data.get("notes") or ""
    cause = data.get("cause") or ""
    solution = data.get("solution") or ""
    in_warranty = data.get("in_warranty")
    if in_warranty is not None and not isinstance(in_warranty, bool):
        # allow truthy string? just coerce if bool else ignore
        # keep as is if not bool - let db store whatever (but spec expects bool)
        # we keep only bool or None
        if isinstance(in_warranty, str):
            low = in_warranty.strip().lower()
            if low in ("true", "1"):
                in_warranty = True
            elif low in ("false", "0"):
                in_warranty = False
            else:
                in_warranty = None

    number = _next_ticket_number()
    # loop if collision (unique)
    for _ in range(5):
        existing = db.session.query(ServiceTicket).filter_by(number=number).first()
        if not existing:
            break
        # bump suffix
        try:
            n = int(number.split("-")[-1]) + 1
        except Exception:
            n = 1
        number = f"CH-{date.today().year}-{n:04d}"
    else:
        number = f"CH-{date.today().year}-{uuid.uuid4().hex[:4].upper()}"

    now = datetime.now(timezone.utc)
    ticket = ServiceTicket(
        number=number,
        client_id=client_id,
        project_id=project_id,
        description=description,
        status=status,
        cost=cost,
        cause=cause,
        solution=solution,
        in_warranty=in_warranty,
        assigned_user_id=assigned_user_id,
        scheduled_at=scheduled_at,
        notes=notes,
        created_by=_creator(),
        opened_at=now,
    )
    # if created already RESOLVIDO/ENCERRADO preenche timestamps
    if status == "RESOLVIDO":
        ticket.resolved_at = now
    elif status == "ENCERRADO":
        ticket.closed_at = now

    db.session.add(ticket)
    db.session.flush()

    if ticket.status == "AGENDADO":
        _ensure_calendar_event(ticket)

    db.session.commit()
    return jsonify(_enrich(ticket)), 201


# ── GET ONE ───────────────────────────────────────────────────────


@bp.get("/api/tickets/<ticket_id>")
@token_required()
def get_ticket(ticket_id):
    t = db.session.get(ServiceTicket, ticket_id)
    if not t:
        return jsonify({"detail": "Chamado nao encontrado"}), 404
    return jsonify(_enrich(t))


# ── UPDATE ────────────────────────────────────────────────────────


@bp.put("/api/tickets/<ticket_id>")
@token_required()
def update_ticket(ticket_id):
    t = db.session.get(ServiceTicket, ticket_id)
    if not t:
        return jsonify({"detail": "Chamado nao encontrado"}), 404
    data = body_json()

    # status validacao
    if "status" in data and data.get("status") not in (None, ""):
        raw = data.get("status")
        st = str(raw).strip().upper() if isinstance(raw, str) else str(raw)
        if st not in VALID_STATUSES:
            return jsonify({"detail": "status invalido"}), 400
    # client_id / project_id / assigned_user_id se presentes
    if "client_id" in data and data.get("client_id") not in (None, ""):
        if not db.session.get(Client, data.get("client_id")):
            return jsonify({"detail": "Cliente nao encontrado"}), 404
    if "project_id" in data and data.get("project_id") not in (None, ""):
        if not db.session.get(Project, data.get("project_id")):
            return jsonify({"detail": "Projeto nao encontrado"}), 404
    if "assigned_user_id" in data and data.get("assigned_user_id") not in (None, ""):
        if not db.session.get(User, data.get("assigned_user_id")):
            return jsonify({"detail": "Usuario nao encontrado"}), 404

    # aplicar campos
    if "description" in data:
        raw = data.get("description")
        if isinstance(raw, str) and not raw.strip():
            return jsonify({"detail": "description e obrigatoria"}), 400
        if isinstance(raw, str):
            t.description = raw.strip()

    if "cost" in data:
        cv = data.get("cost")
        if cv is not None and cv != "":
            try:
                c = float(cv)
            except (TypeError, ValueError):
                return jsonify({"detail": "cost invalido"}), 400
            if c < 0:
                return jsonify({"detail": "cost deve ser maior ou igual a zero"}), 400
            import math
            if math.isnan(c) or math.isinf(c):
                return jsonify({"detail": "cost invalido"}), 400
            t.cost = c
        else:
            t.cost = 0

    if "cause" in data:
        t.cause = data.get("cause") or ""
    if "solution" in data:
        t.solution = data.get("solution") or ""
    if "in_warranty" in data:
        v = data.get("in_warranty")
        if v is not None and not isinstance(v, bool):
            if isinstance(v, str):
                low = v.strip().lower()
                if low in ("true", "1"):
                    v = True
                elif low in ("false", "0"):
                    v = False
                else:
                    v = None
        t.in_warranty = v
    if "assigned_user_id" in data:
        v = data.get("assigned_user_id")
        t.assigned_user_id = None if v in (None, "") else v
    if "scheduled_at" in data:
        v = data.get("scheduled_at")
        if v in (None, ""):
            t.scheduled_at = None
        else:
            try:
                d = parse_date(v)
            except Exception:
                return jsonify({"detail": "scheduled_at invalida"}), 400
            if d is None:
                return jsonify({"detail": "scheduled_at invalida"}), 400
            t.scheduled_at = d
    if "notes" in data:
        t.notes = data.get("notes") or ""
    if "project_id" in data:
        v = data.get("project_id")
        t.project_id = None if v in (None, "") else v
    if "client_id" in data:
        v = data.get("client_id")
        if v not in (None, ""):
            t.client_id = v

    if "status" in data and data.get("status") not in (None, ""):
        raw = data.get("status")
        st = str(raw).strip().upper() if isinstance(raw, str) else str(raw)
        # aplica status
        prev = t.status
        t.status = st
        now = datetime.now(timezone.utc)
        if st == "RESOLVIDO" and t.resolved_at is None:
            t.resolved_at = now
        if st == "ENCERRADO" and t.closed_at is None:
            t.closed_at = now
        # agenda automatica quando vai para AGENDADO
        if st == "AGENDADO":
            _ensure_calendar_event(t)

    # se custo/assigned etc mudaram enquanto ja AGENDADO com evento existente, sincroniza evento
    # (quando assigned_user_id ou scheduled_at mudaram e status continua AGENDADO)
    if t.status == "AGENDADO" and t.calendar_event_id is not None:
        ev = db.session.get(CalendarEvent, t.calendar_event_id)
        if ev:
            # sync if changed but keep same id
            if "scheduled_at" in data or "assigned_user_id" in data or "description" in data or "client_id" in data or "project_id" in data:
                ev.start_date = t.scheduled_at or ev.start_date
                if "assigned_user_id" in data:
                    ev.assigned_user_id = t.assigned_user_id
                if "client_id" in data:
                    ev.client_id = t.client_id
                if "project_id" in data:
                    ev.project_id = t.project_id
                if "description" in data:
                    ev.title = f"Assistencia {t.number}: {t.description[:50]}"
                    ev.description = f"Chamado {t.number} - {t.description[:100]}"

    db.session.commit()
    return jsonify(_enrich(t))


# ── DELETE ────────────────────────────────────────────────────────


@bp.delete("/api/tickets/<ticket_id>")
@token_required()
def delete_ticket(ticket_id):
    t = db.session.get(ServiceTicket, ticket_id)
    if not t:
        return jsonify({"detail": "Chamado nao encontrado"}), 404
    # so ABERTO/EM_ANALISE pode apagar - resto 400 historico imutavel
    if t.status not in ("ABERTO", "EM_ANALISE"):
        return jsonify({"detail": "Chamado nao pode ser removido neste status"}), 400
    # remove arquivos do disco como attachments_bp faz
    photos = list(t.photos)
    db.session.delete(t)
    db.session.commit()
    for p in photos:
        try:
            path = os.path.join(_upload_dir(), p.stored_name)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
    return jsonify({"ok": True})


# ── PHOTOS ────────────────────────────────────────────────────────


@bp.post("/api/tickets/<ticket_id>/photos")
@token_required()
def upload_photo(ticket_id):
    t = db.session.get(ServiceTicket, ticket_id)
    if not t:
        return jsonify({"detail": "Chamado nao encontrado"}), 404
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"detail": "Arquivo obrigatorio (campo 'file')"}), 400
    original = secure_filename(file.filename) or "arquivo"
    if len(original) > 255:
        stem, ext = os.path.splitext(original)
        original = (stem[: max(0, 255 - len(ext))] + ext)[:255]
    ext = os.path.splitext(original)[1].lower()
    stored = uuid.uuid4().hex + ext
    path = os.path.join(_upload_dir(), stored)
    file.save(path)
    row = TicketPhoto(
        ticket_id=ticket_id,
        filename=original,
        stored_name=stored,
        mime_type=file.mimetype or "",
        size=os.path.getsize(path),
        created_by=_creator(),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@bp.get("/api/tickets/photos/<photo_id>/download")
@token_required()
def download_photo(photo_id):
    row = db.session.get(TicketPhoto, photo_id)
    if not row:
        return jsonify({"detail": "Foto nao encontrada"}), 404
    path = os.path.join(_upload_dir(), row.stored_name)
    if not os.path.exists(path):
        return jsonify({"detail": "Arquivo ausente no disco"}), 404
    return send_file(path, mimetype=row.mime_type or "application/octet-stream", as_attachment=True, download_name=row.filename)


@bp.delete("/api/tickets/photos/<photo_id>")
@token_required()
def delete_photo(photo_id):
    row = db.session.get(TicketPhoto, photo_id)
    if not row:
        return jsonify({"detail": "Foto nao encontrada"}), 404
    path = os.path.join(_upload_dir(), row.stored_name)
    db.session.delete(row)
    db.session.commit()
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
    return jsonify({"ok": True})
