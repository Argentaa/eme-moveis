"""CRUD /api/calendar e /api/calendar/notifications."""
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request

from app.helpers import body_json, parse_date, parse_time
from app.auth import token_required
from app.extensions import db
from app.models.models import CalendarEvent, Notification, Project, StockItem

bp = Blueprint("calendar", __name__)

EVENT_FIELDS = (
    "title", "description", "type", "status", "start_date", "start_time",
    "end_date", "end_time", "project_id", "client_id", "assigned_user_id", "observations",
)


def _apply(data, ev):
    for f in EVENT_FIELDS:
        if f in data:
            v = data[f]
            if f in ("start_date", "end_date"):
                v = parse_date(v)
            elif f in ("start_time", "end_time"):
                v = parse_time(v)
            elif f in ("project_id", "client_id", "assigned_user_id") and v == "":
                v = None
            setattr(ev, f, v)


@bp.get("/api/calendar/today")
@token_required()
def today_events():
    t = date.today()
    rows = (
        db.session.query(CalendarEvent).filter(CalendarEvent.start_date == t).order_by(CalendarEvent.start_time).all()
    )
    return jsonify([e.to_dict() for e in rows])


@bp.get("/api/calendar/week")
@token_required()
def week_events():
    t = date.today()
    start = t - timedelta(days=t.weekday())
    end = start + timedelta(days=6)
    rows = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.start_date >= start, CalendarEvent.start_date <= end)
        .order_by(CalendarEvent.start_date, CalendarEvent.start_time)
        .all()
    )
    return jsonify([e.to_dict() for e in rows])


@bp.get("/api/calendar")
@token_required()
def list_events():
    q = db.session.query(CalendarEvent)
    client_id = request.args.get("client_id") or None
    if client_id:
        q = q.filter_by(client_id=client_id)
    try:
        month = int(request.args.get("month") or 0)
        year = int(request.args.get("year") or 0)
    except (TypeError, ValueError):
        month, year = 0, 0
    if month and year:
        from sqlalchemy import and_, extract

        q = q.filter(extract("month", CalendarEvent.start_date) == month, extract("year", CalendarEvent.start_date) == year)
    elif year:
        from sqlalchemy import extract

        q = q.filter(extract("year", CalendarEvent.start_date) == year)
    rows = q.order_by(CalendarEvent.start_date, CalendarEvent.start_time).all()
    return jsonify([e.to_dict() for e in rows])


@bp.post("/api/calendar")
@token_required()
def create_event():
    data = body_json()
    if not (data.get("title") or "").strip():
        return jsonify({"detail": "title e obrigatorio"}), 400
    if not data.get("start_date"):
        return jsonify({"detail": "start_date e obrigatoria"}), 400
    ev = CalendarEvent(title=data["title"].strip())
    _apply(data, ev)
    db.session.add(ev)
    db.session.commit()
    return jsonify(ev.to_dict()), 201


@bp.put("/api/calendar/<event_id>")
@token_required()
def update_event(event_id):
    ev = db.session.get(CalendarEvent, event_id)
    if not ev:
        return jsonify({"detail": "Evento nao encontrado"}), 404
    _apply(body_json(), ev)
    db.session.commit()
    return jsonify(ev.to_dict())


@bp.delete("/api/calendar/<event_id>")
@token_required()
def delete_event(event_id):
    ev = db.session.get(CalendarEvent, event_id)
    if not ev:
        return jsonify({"detail": "Evento nao encontrado"}), 404
    db.session.delete(ev)
    db.session.commit()
    return jsonify({"ok": True})


# ── Notificacoes ──────────────────────────────────────────────

def _notif_query():
    q = db.session.query(Notification)
    if hasattr(g, "current_user"):
        q = q.filter(
            (Notification.user_id.is_(None)) | (Notification.user_id == g.current_user.id)
        )
    return q


@bp.get("/api/calendar/notifications")
@token_required()
def list_notifications():
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    q = _notif_query()
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in rows])


@bp.get("/api/calendar/notifications/count")
@token_required()
def count_notifications():
    total = _notif_query().filter(Notification.read_at.is_(None)).count()
    return jsonify({"unread": total, "count": total})


@bp.put("/api/calendar/notifications/<notif_id>/read")
@token_required()
def mark_read(notif_id):
    notif = db.session.get(Notification, notif_id)
    if not notif:
        return jsonify({"detail": "Notificacao nao encontrada"}), 404
    notif.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(notif.to_dict())


@bp.put("/api/calendar/notifications/read-all")
@token_required()
def mark_all_read():
    now = datetime.now(timezone.utc)
    for n in _notif_query().filter(Notification.read_at.is_(None)).all():
        n.read_at = now
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/calendar/notifications/generate-alerts")
@token_required()
def generate_alerts():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    created = 0

    def exists(ntype, event_id=None, project_id=None):
        q = db.session.query(Notification).filter_by(type=ntype, event_id=event_id, project_id=project_id)
        return db.session.query(q.exists()).scalar()

    for ev in db.session.query(CalendarEvent).filter(CalendarEvent.start_date == today).all():
        if not exists("EVENTO_HOJE", event_id=ev.id):
            db.session.add(Notification(title=f"Evento hoje: {ev.title}", message=f"{ev.title} acontece hoje.", type="EVENTO_HOJE", event_id=ev.id))
            created += 1
    for ev in db.session.query(CalendarEvent).filter(CalendarEvent.start_date == tomorrow).all():
        if not exists("EVENTO_AMANHA", event_id=ev.id):
            db.session.add(Notification(title=f"Evento amanha: {ev.title}", message=f"{ev.title} acontece amanha.", type="EVENTO_AMANHA", event_id=ev.id))
            created += 1
    for p in db.session.query(Project).filter(Project.deadline < today, Project.status != "CONCLUIDO").all():
        if not exists("PROJETO_ATRASADO", project_id=p.id):
            db.session.add(Notification(title=f"Projeto atrasado: {p.title}", message=f"O projeto {p.title} esta com prazo vencido.", type="PROJETO_ATRASADO", project_id=p.id))
            created += 1
    for p in db.session.query(Project).filter(Project.deadline != None, Project.status != "CONCLUIDO").all():
        try:
            delta = (p.deadline - date.today()).days
        except Exception:
            continue
        if 0 <= delta <= 7 and not exists("PROJETO_PROXIMO", project_id=p.id):
            db.session.add(Notification(title=f"Projeto proximo do prazo: {p.title}", message=f"O projeto {p.title} vence em {delta} dias.", type="PROJETO_PROXIMO", project_id=p.id))
            created += 1
    for item in db.session.query(StockItem).all():
        try:
            low = float(item.quantity or 0) <= float(item.min_quantity or 0)
        except (TypeError, ValueError):
            low = False
        if low and not exists("ESTOQUE_BAIXO"):
            db.session.add(Notification(title=f"Estoque baixo: {item.name}", message=f"O item {item.name} atingiu o estoque minimo.", type="ESTOQUE_BAIXO"))
            created += 1
            break
    from app.models.models import ServiceTicket
    pending = db.session.query(ServiceTicket).filter(ServiceTicket.status != 'ENCERRADO').count()
    if pending > 0 and not exists('CHAMADO_PENDENTE'):
        db.session.add(Notification(title=f'{pending} chamados pendentes', message=f'Existem {pending} chamados de assistência pendentes.', type='CHAMADO_PENDENTE'))
        created += 1
    db.session.commit()
    return jsonify({"ok": True, "generated": created})
