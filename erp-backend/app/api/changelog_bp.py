"""Novidades: registro de atualizacoes do sistema (changelog)."""
from flask import Blueprint, g, jsonify

from app.helpers import body_json, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import ChangelogEntry

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


@bp.get("/api/changelog")
@token_required()
def list_entries():
    rows = db.session.query(ChangelogEntry).order_by(ChangelogEntry.entry_date.desc(), ChangelogEntry.created_at.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/changelog")
@token_required()
def create_entry():
    data = body_json()
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"detail": "title e obrigatorio"}), 400
    row = ChangelogEntry(title=title, created_by=g.current_user.username if hasattr(g, "current_user") else "")
    _apply(data, row)
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


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
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})
