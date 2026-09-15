"""GET/PUT /api/funnel-columns e CRUD /api/funnels + colunas dinamicas."""
import re
import unicodedata

from flask import Blueprint, jsonify, request

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import Client, Funnel, FunnelColumn, Project

bp = Blueprint("funnel", __name__)


def _default_funnel(kind):
    return db.session.query(Funnel).filter_by(kind=kind, is_default=True).first()


def _funnel_or_404(fid):
    funnel = db.session.get(Funnel, fid)
    if not funnel:
        return None
    return funnel


def _slug(label):
    s = (label or "").strip()
    if not s:
        return "ETAPA"
    # normaliza acentos -> ascii
    s = unicodedata.normalize("NFD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.upper().strip()
    if not s:
        return "ETAPA"
    # substitui sequencias nao alfanumericas por _
    s = re.sub(r"[^A-Z0-9]+", "_", s)
    s = s.strip("_")
    # remove _ duplicados
    s = re.sub(r"_+", "_", s)
    if not s:
        return "ETAPA"
    return s


def _key_unico(funnel, base):
    key = base
    suffix = 2
    while db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id, column_key=key).first():
        key = base + "_" + str(suffix)
        suffix += 1
    return key


@bp.get("/api/funnels")
@token_required()
def list_funnels():
    kind = request.args.get("kind")
    q = db.session.query(Funnel)
    if kind:
        kind = kind.upper()
        q = q.filter(Funnel.kind == kind)
    rows = q.order_by(Funnel.kind, Funnel.is_default.desc(), Funnel.name).all()
    return jsonify([f.to_dict() for f in rows])


@bp.post("/api/funnels")
@token_required()
def create_funnel():
    data = body_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    kind = (data.get("kind") or "CRM")
    kind = str(kind).strip().upper()
    if kind not in ("CRM", "PROJECTS"):
        return jsonify({"detail": "kind invalido"}), 400
    funnel = Funnel(name=name, kind=kind, is_default=False, active=True)
    db.session.add(funnel)
    db.session.flush()
    default = _default_funnel(kind)
    if default:
        cols = db.session.query(FunnelColumn).filter_by(funnel_id=default.id).order_by(FunnelColumn.position).all()
        for col in cols:
            clone = FunnelColumn(
                column_key=col.column_key,
                label=col.label,
                description=col.description,
                type=col.type,
                funnel_id=funnel.id,
                position=col.position,
            )
            db.session.add(clone)
    db.session.commit()
    return jsonify(funnel.to_dict()), 201


@bp.put("/api/funnels/<funnel_id>")
@token_required()
def update_funnel(funnel_id):
    funnel = _funnel_or_404(funnel_id)
    if not funnel:
        return jsonify({"detail": "Funil nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"detail": "name e obrigatorio"}), 400
        funnel.name = name
    if "active" in data:
        funnel.active = bool(data.get("active"))
    db.session.commit()
    return jsonify(funnel.to_dict())


@bp.delete("/api/funnels/<funnel_id>")
@token_required()
def delete_funnel(funnel_id):
    funnel = _funnel_or_404(funnel_id)
    if not funnel:
        return jsonify({"detail": "Funil nao encontrado"}), 404
    if funnel.is_default:
        return jsonify({"detail": "Funil padrao nao pode ser excluido"}), 400
    has_client = db.session.query(Client).filter_by(funnel_id=funnel.id).first()
    has_project = db.session.query(Project).filter_by(funnel_id=funnel.id).first()
    if has_client or has_project:
        return jsonify({"detail": "Funil em uso"}), 400
    db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id).delete()
    db.session.delete(funnel)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/funnels/<funnel_id>/columns")
@token_required()
def create_funnel_column(funnel_id):
    funnel = _funnel_or_404(funnel_id)
    if not funnel:
        return jsonify({"detail": "Funil nao encontrado"}), 404
    data = body_json()
    label = (data.get("label") or "").strip()
    if not label:
        return jsonify({"detail": "label e obrigatorio"}), 400
    base = _slug(label)
    key = _key_unico(funnel, base)
    existing = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id).all()
    if existing:
        max_pos = max(c.position for c in existing)
        position = max_pos + 1
    else:
        position = 0
    col = FunnelColumn(
        column_key=key,
        label=label,
        type=funnel.kind,
        funnel_id=funnel.id,
        position=position,
    )
    if "description" in data:
        col.description = data.get("description")
    db.session.add(col)
    db.session.commit()
    return jsonify(col.to_dict()), 201


@bp.put("/api/funnels/<funnel_id>/columns/<column_key>")
@token_required()
def update_funnel_column(funnel_id, column_key):
    funnel = _funnel_or_404(funnel_id)
    if not funnel:
        return jsonify({"detail": "Funil nao encontrado"}), 404
    key = (column_key or "").upper()
    col = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id, column_key=key).first()
    if not col:
        return jsonify({"detail": "Etapa nao encontrada"}), 404
    data = body_json()
    if "label" in data:
        label = (data.get("label") or "").strip()
        if not label:
            return jsonify({"detail": "label e obrigatorio"}), 400
        col.label = label
    if "description" in data:
        col.description = data.get("description")
    if "position" in data:
        try:
            col.position = int(data.get("position"))
        except (TypeError, ValueError):
            return jsonify({"detail": "position invalida"}), 400
    db.session.commit()
    return jsonify(col.to_dict())


@bp.delete("/api/funnels/<funnel_id>/columns/<column_key>")
@token_required()
def delete_funnel_column(funnel_id, column_key):
    funnel = _funnel_or_404(funnel_id)
    if not funnel:
        return jsonify({"detail": "Funil nao encontrado"}), 404
    key = (column_key or "").upper()
    col = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id, column_key=key).first()
    if not col:
        return jsonify({"detail": "Etapa nao encontrada"}), 404
    has_client = db.session.query(Client).filter_by(funnel_id=funnel.id, funnel_status=key).first()
    has_project = db.session.query(Project).filter_by(funnel_id=funnel.id, status=key).first()
    if has_client or has_project:
        return jsonify({"detail": "Ha cards nesta etapa"}), 400
    db.session.delete(col)
    db.session.commit()
    return jsonify({"ok": True})


# --- LEGADOS (mantidos) ---

@bp.get("/api/funnel-columns")
@token_required()
def list_columns():
    ctype = request.args.get("type", "CRM").upper()
    funnel = _default_funnel(ctype)
    if funnel:
        rows = (
            db.session.query(FunnelColumn)
            .filter_by(funnel_id=funnel.id)
            .order_by(FunnelColumn.position, FunnelColumn.label)
            .all()
        )
    else:
        rows = (
            db.session.query(FunnelColumn)
            .filter_by(type=ctype)
            .filter(FunnelColumn.funnel_id.is_(None))
            .order_by(FunnelColumn.column_key)
            .all()
        )
    return jsonify([c.to_dict() for c in rows])


@bp.put("/api/funnel-columns")
@token_required()
def bulk_update():
    """Atualizacao em lote: aceita lista ou {\"columns\": [...]}."""
    data = request.get_json(silent=True)
    items = data if isinstance(data, list) else (data or {}).get("columns", [])
    updated = []
    for item in items:
        key = (item.get("column_key") or "").upper()
        ctype = (item.get("type") or "CRM").upper()
        if not key:
            continue
        funnel = _default_funnel(ctype)
        if not funnel:
            continue
        col = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id, column_key=key).first()
        if not col:
            existing = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id).all()
            if existing:
                max_pos = max(c.position for c in existing)
                pos = max_pos + 1
            else:
                pos = 0
            col = FunnelColumn(column_key=key, type=ctype, funnel_id=funnel.id, position=pos)
            db.session.add(col)
        if "label" in item:
            col.label = item["label"]
        if "description" in item:
            col.description = item["description"]
        updated.append(col)
    db.session.commit()
    return jsonify([c.to_dict() for c in updated])


@bp.put("/api/funnel-columns/<column_key>")
@token_required()
def update_column(column_key):
    ctype = request.args.get("type", "CRM").upper()
    data = body_json()
    if data.get("type"):
        ctype = str(data["type"]).upper()
    key = (column_key or "").upper()
    funnel = _default_funnel(ctype)
    if not funnel:
        return jsonify({"detail": "Funil nao encontrado"}), 404
    col = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id, column_key=key).first()
    if not col:
        existing = db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id).all()
        if existing:
            max_pos = max(c.position for c in existing)
            pos = max_pos + 1
        else:
            pos = 0
        col = FunnelColumn(column_key=key, type=ctype, funnel_id=funnel.id, position=pos)
        db.session.add(col)
    if "label" in data:
        col.label = data["label"]
    if "description" in data:
        col.description = data["description"]
    db.session.commit()
    return jsonify(col.to_dict())
