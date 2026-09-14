"""Upload/download de anexos de clientes (plantas, contratos, propostas PDF)."""
import os
import uuid

from flask import Blueprint, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.auth import token_required
from app.extensions import db
from app.models.models import Attachment, Client

bp = Blueprint("attachments", __name__)


def _upload_dir():
    d = current_app.config["UPLOAD_DIR"]
    os.makedirs(d, exist_ok=True)
    return d


def _creator():
    return g.current_user.username if hasattr(g, "current_user") else ""


@bp.get("/api/clients/<client_id>/attachments")
@token_required()
def list_attachments(client_id):
    rows = (db.session.query(Attachment).filter_by(client_id=client_id)
            .order_by(Attachment.created_at.desc()).all())
    return jsonify([a.to_dict() for a in rows])


@bp.post("/api/clients/<client_id>/attachments")
@token_required()
def upload_attachment(client_id):
    if not db.session.get(Client, client_id):
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"detail": "Arquivo obrigatorio (campo 'file')"}), 400
    original = secure_filename(file.filename) or "arquivo"
    if len(original) > 255:
        stem, ext = os.path.splitext(original)
        original = (stem[:max(0, 255 - len(ext))] + ext)[:255]
    ext = os.path.splitext(original)[1].lower()
    stored = uuid.uuid4().hex + ext
    path = os.path.join(_upload_dir(), stored)
    file.save(path)
    row = Attachment(client_id=client_id, filename=original, stored_name=stored,
                     mime_type=file.mimetype or "", size=os.path.getsize(path),
                     created_by=_creator())
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@bp.get("/api/attachments/<attachment_id>/download")
@token_required()
def download_attachment(attachment_id):
    row = db.session.get(Attachment, attachment_id)
    if not row:
        return jsonify({"detail": "Anexo nao encontrado"}), 404
    path = os.path.join(_upload_dir(), row.stored_name)
    if not os.path.exists(path):
        return jsonify({"detail": "Arquivo ausente no disco"}), 404
    return send_file(path, mimetype=row.mime_type or "application/octet-stream",
                     as_attachment=True, download_name=row.filename)


@bp.delete("/api/attachments/<attachment_id>")
@token_required()
def delete_attachment(attachment_id):
    row = db.session.get(Attachment, attachment_id)
    if not row:
        return jsonify({"detail": "Anexo nao encontrado"}), 404
    path = os.path.join(_upload_dir(), row.stored_name)
    db.session.delete(row)
    db.session.commit()
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass  # registro no banco ja removido; arquivo orfao tolerado
    return jsonify({"ok": True})