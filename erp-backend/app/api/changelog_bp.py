"""Novidades: registro de atualizacoes do sistema (changelog) + lido / nao lido."""
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify

from app.helpers import body_json, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import ChangelogEntry, ChangelogRead

bp = Blueprint("changelog", __name__)

FIELDS = ("title", "content", "category", "entry_date")


def _apply(data, row):
    for f in FIELDS:
        if f not in data:
            continue
        v = data[f]
        if f == "entry_date":
            v = parse_date(v)
        setattr(row, f, v)


# ── Lido / nao lido ───────────────────────────────────────────

def _current_user_id():
    if hasattr(g, "current_user") and g.current_user is not None:
        return g.current_user.id
    return None


def _read_ids(user_id):
    if not user_id:
        return set()
    rows = db.session.query(ChangelogRead.entry_id).filter(
        ChangelogRead.user_id == user_id
    ).all()
    return {r[0] for r in rows}


def _ensure_baseline(user_id):
    """Primeira visita do usuario: tudo que ja existe conta como lido.

    Sem isso, um usuario recem-criado (ou a base inteira no dia do deploy)
    veria o historico completo como nao lido. Roda uma unica vez por usuario:
    a partir dai, o que chegar de novo aparece como nao lido.
    """
    if not user_id:
        return
    already = db.session.query(ChangelogRead.id).filter(
        ChangelogRead.user_id == user_id
    ).first()
    if already:
        return
    entry_ids = db.session.query(ChangelogEntry.id).all()
    if not entry_ids:
        return
    now = datetime.now(timezone.utc)
    for (entry_id,) in entry_ids:
        db.session.add(ChangelogRead(user_id=user_id, entry_id=entry_id, read_at=now))
    db.session.commit()


def _unread_total(user_id):
    total = db.session.query(ChangelogEntry.id).count()
    return max(0, total - len(_read_ids(user_id)))


@bp.get("/api/changelog/unread-count")
@token_required()
def unread_count():
    user_id = _current_user_id()
    _ensure_baseline(user_id)
    unread = _unread_total(user_id)
    return jsonify({"unread": unread, "count": unread})


@bp.post("/api/changelog/read-all")
@token_required()
def mark_all_read():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"detail": "Usuario nao identificado"}), 401
    _ensure_baseline(user_id)
    read = _read_ids(user_id)
    now = datetime.now(timezone.utc)
    marked = 0
    for (entry_id,) in db.session.query(ChangelogEntry.id).all():
        if entry_id in read:
            continue
        db.session.add(ChangelogRead(user_id=user_id, entry_id=entry_id, read_at=now))
        marked += 1
    db.session.commit()
    return jsonify({"ok": True, "marked": marked, "unread": 0, "count": 0})


@bp.put("/api/changelog/<entry_id>/read")
@token_required()
def mark_entry_read(entry_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"detail": "Usuario nao identificado"}), 401
    row = db.session.get(ChangelogEntry, entry_id)
    if not row:
        return jsonify({"detail": "Novidade nao encontrada"}), 404
    existing = db.session.query(ChangelogRead).filter(
        ChangelogRead.user_id == user_id, ChangelogRead.entry_id == entry_id
    ).first()
    if not existing:
        db.session.add(
            ChangelogRead(user_id=user_id, entry_id=entry_id, read_at=datetime.now(timezone.utc))
        )
        db.session.commit()
    unread = _unread_total(user_id)
    return jsonify({"ok": True, "entry_id": entry_id, "unread": unread, "count": unread})


# ── CRUD ──────────────────────────────────────────────────────

@bp.get("/api/changelog")
@token_required()
def list_entries():
    user_id = _current_user_id()
    _ensure_baseline(user_id)
    read = _read_ids(user_id)
    rows = db.session.query(ChangelogEntry).order_by(
        ChangelogEntry.entry_date.desc(), ChangelogEntry.created_at.desc()
    ).all()
    out = []
    for r in rows:
        data = r.to_dict()
        data["read"] = r.id in read
        out.append(data)
    return jsonify(out)


@bp.post("/api/changelog")
@token_required()
def create_entry():
    data = body_json()
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"detail": "title e obrigatorio"}), 400
    user_id = _current_user_id()
    row = ChangelogEntry(title=title, created_by=g.current_user.username if hasattr(g, "current_user") else "")
    _apply(data, row)
    db.session.add(row)
    db.session.flush()
    # Quem publica ja sabe o que publicou: nao entra como nao lido para ele.
    if user_id:
        db.session.add(
            ChangelogRead(user_id=user_id, entry_id=row.id, read_at=datetime.now(timezone.utc))
        )
    db.session.commit()
    out = row.to_dict()
    out["read"] = True
    return jsonify(out), 201


@bp.put("/api/changelog/<entry_id>")
@token_required()
def update_entry(entry_id):
    row = db.session.get(ChangelogEntry, entry_id)
    if not row:
        return jsonify({"detail": "Novidade nao encontrada"}), 404
    data = body_json()
    if "title" in data and not (data.get("title") or "").strip():
        return jsonify({"detail": "title e obrigatorio"}), 400
    _apply(data, row)
    db.session.commit()
    return jsonify(row.to_dict())


@bp.delete("/api/changelog/<entry_id>")
@token_required()
def delete_entry(entry_id):
    row = db.session.get(ChangelogEntry, entry_id)
    if not row:
        return jsonify({"detail": "Novidade nao encontrada"}), 404
    db.session.query(ChangelogRead).filter(ChangelogRead.entry_id == entry_id).delete()
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})
