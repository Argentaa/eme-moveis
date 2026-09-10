"""Backend Flask do site institucional eMe Móveis.

Replica o contrato do server.ts (Node) para o frontend React continuar funcionando:
auth JWT, upload, projects, timeline, settings + health e contact-info.
"""
from __future__ import annotations

import json
import logging
import os
import uuid

import bcrypt
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import text
from werkzeug.utils import secure_filename

from auth import create_token, require_auth
from models import SiteProject, SiteSettings, SiteTimeline, SiteUser, db
from seed import seed_initial_data

log = logging.getLogger(__name__)

ALLOWED_FOLDERS = {"projetos", "timeline", "equipe", "site-assets"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB


def _database_uri() -> str:
    uri = os.environ.get("DATABASE_URL", "").strip()
    if uri:
        return uri
    return "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "site.db")


def _upload_dir() -> str:
    return os.environ.get("UPLOAD_DIR", "/app/uploads")


def _ensure_upload_dirs(base: str) -> None:
    os.makedirs(base, exist_ok=True)
    for folder in ALLOWED_FOLDERS:
        os.makedirs(os.path.join(base, folder), exist_ok=True)


def _parse_album(raw) -> list:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (ValueError, TypeError):
            pass
        return [raw] if raw else []
    return []


def _parse_address(raw):
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"value": raw}
        except (ValueError, TypeError):
            return {"value": raw}
    return None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Defesa em profundidade: limite global + checagem manual por arquivo.
    app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

    CORS(app)
    db.init_app(app)

    upload_base = _upload_dir()
    _ensure_upload_dirs(upload_base)

    with app.app_context():
        db.create_all()
        seed_initial_data()

    # ------------------------------------------------------------------ auth
    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify({"error": "Usuário e senha são obrigatórios."}), 400
        user = SiteUser.query.filter_by(username=username).first()
        if user is None or not bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            return jsonify({"error": "Usuário ou senha incorretos."}), 401
        try:
            token = create_token(user.id, user.username)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify({"success": True, "token": token, "user": user.to_dict()})

    @app.post("/api/auth/update-credentials")
    @require_auth
    def update_credentials():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username:
            return jsonify({"error": "O nome de usuário é obrigatório."}), 400
        claims = getattr(request, "auth_claims", {})
        try:
            user_id = int(claims.get("sub", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Token inválido ou expirado."}), 403
        user = db.session.get(SiteUser, user_id)
        if user is None:
            return jsonify({"error": "Administrador não encontrado."}), 404
        conflict = SiteUser.query.filter(
            SiteUser.username == username, SiteUser.id != user.id
        ).first()
        if conflict is not None:
            return jsonify({"error": "Nome de usuário já em uso."}), 409
        user.username = username
        if password:
            user.password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
        db.session.commit()
        return jsonify(
            {"success": True, "message": "Credenciais de administrador alteradas com sucesso."}
        )

    # ---------------------------------------------------------------- upload
    @app.post("/api/upload")
    @require_auth
    def upload():
        folder = (request.args.get("folder") or "projetos").strip()
        if folder not in ALLOWED_FOLDERS:
            return jsonify({"error": f"Pasta inválida. Use uma de: {sorted(ALLOWED_FOLDERS)}."}), 400
        if "file" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado."}), 400
        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"error": "Nenhum arquivo enviado."}), 400
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Tipo de arquivo não permitido. Use jpg, jpeg, png ou webp."}), 400
        data = f.read()
        if len(data) > MAX_UPLOAD_BYTES:
            return jsonify({"error": "Arquivo excede o limite de 5MB."}), 413
        if not data:
            return jsonify({"error": "Arquivo vazio."}), 400
        safe_base = secure_filename(f.filename.rsplit(".", 1)[0]) or "arquivo"
        filename = f"file-{uuid.uuid4().hex}-{safe_base}.{ext}"
        dest_dir = os.path.join(_upload_dir(), folder)
        os.makedirs(dest_dir, exist_ok=True)
        with open(os.path.join(dest_dir, filename), "wb") as fh:
            fh.write(data)
        return jsonify({"success": True, "filePath": f"/uploads/{folder}/{filename}"})

    @app.get("/uploads/<path:filename>")
    def serve_upload(filename: str):
        return send_from_directory(_upload_dir(), filename)

    # --------------------------------------------------------------- projects
    @app.get("/api/projects")
    def list_projects():
        projects = SiteProject.query.order_by(SiteProject.id.desc()).all()
        return jsonify([p.to_dict() for p in projects])

    @app.post("/api/projects")
    @require_auth
    def add_project():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        category = (data.get("category") or "").strip()
        image = (data.get("image") or data.get("mainImage") or "").strip()
        if not title or not category or not image:
            return jsonify({"error": "Título, Categoria e Imagem são obrigatórios."}), 400
        album = _parse_album(data.get("album")) or [image]
        project = SiteProject(
            title=title,
            category=category,
            image=image,
            album=album,
            description=data.get("description") or "",
        )
        db.session.add(project)
        db.session.commit()
        return jsonify(project.to_dict()), 201

    @app.put("/api/projects/<int:project_id>")
    @require_auth
    def update_project(project_id: int):
        project = db.session.get(SiteProject, project_id)
        if project is None:
            return jsonify({"error": "Projeto não encontrado."}), 404
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        category = (data.get("category") or "").strip()
        image = (data.get("image") or data.get("mainImage") or "").strip()
        if not title or not category or not image:
            return jsonify({"error": "Título, Categoria e Imagem são obrigatórios."}), 400
        project.title = title
        project.category = category
        project.image = image
        project.album = _parse_album(data.get("album")) or [image]
        project.description = data.get("description") or ""
        db.session.commit()
        return jsonify({"success": True, "message": "Projeto atualizado com sucesso."})

    @app.delete("/api/projects/<int:project_id>")
    @require_auth
    def delete_project(project_id: int):
        project = db.session.get(SiteProject, project_id)
        if project is None:
            return jsonify({"error": "Projeto não encontrado."}), 404
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True, "message": "Projeto excluído com sucesso."})

    # --------------------------------------------------------------- timeline
    @app.get("/api/timeline")
    def list_timeline():
        items = SiteTimeline.query.order_by(SiteTimeline.year.asc(), SiteTimeline.id.asc()).all()
        return jsonify([t.to_dict() for t in items])

    @app.post("/api/timeline")
    @require_auth
    def add_timeline():
        data = request.get_json(silent=True) or {}
        year = str(data.get("year") or "").strip()
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        if not year or not title or not description:
            return jsonify({"error": "Ano, Título e Descrição são obrigatórios."}), 400
        item = SiteTimeline(
            year=year,
            title=title,
            description=description,
            image=(data.get("image") or "").strip() or None,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201

    @app.put("/api/timeline/<int:item_id>")
    @require_auth
    def update_timeline(item_id: int):
        item = db.session.get(SiteTimeline, item_id)
        if item is None:
            return jsonify({"error": "Item não encontrado."}), 404
        data = request.get_json(silent=True) or {}
        year = str(data.get("year") or "").strip()
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        if not year or not title or not description:
            return jsonify({"error": "Ano, Título e Descrição são obrigatórios."}), 400
        item.year = year
        item.title = title
        item.description = description
        item.image = (data.get("image") or "").strip() or None
        db.session.commit()
        return jsonify({"success": True, "message": "Item da linha do tempo atualizado."})

    @app.delete("/api/timeline/<int:item_id>")
    @require_auth
    def delete_timeline(item_id: int):
        item = db.session.get(SiteTimeline, item_id)
        if item is None:
            return jsonify({"error": "Item não encontrado."}), 404
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": "Item excluído com sucesso."})

    # --------------------------------------------------------------- settings
    @app.get("/api/settings")
    def get_settings():
        settings = db.session.get(SiteSettings, 1)
        if settings is None:
            return jsonify({"heroImage": "", "aboutImage": "", "whatsapp": "", "instagram": "", "address": {}})
        return jsonify(settings.to_dict())

    @app.post("/api/settings")
    @require_auth
    def save_settings():
        data = request.get_json(silent=True) or {}
        settings = db.session.get(SiteSettings, 1)
        if settings is None:
            settings = SiteSettings(id=1)
            db.session.add(settings)
        if "heroImage" in data:
            settings.hero_image = (data.get("heroImage") or "").strip() or None
        if "aboutImage" in data:
            settings.about_image = (data.get("aboutImage") or "").strip() or None
        if "whatsapp" in data:
            settings.whatsapp = (data.get("whatsapp") or "").strip() or None
        if "instagram" in data:
            settings.instagram = (data.get("instagram") or "").strip() or None
        if "address" in data or "addressJson" in data:
            parsed = _parse_address(data.get("address", data.get("addressJson")))
            if parsed is not None:
                settings.address_json = parsed
        db.session.commit()
        return jsonify({"success": True, "message": "Configurações atualizadas com sucesso."})

    # --------------------------------------------------- health / contact-info
    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        status = 200 if db_ok else 503
        return jsonify({"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}), status

    @app.get("/api/contact-info")
    def contact_info():
        settings = db.session.get(SiteSettings, 1)
        return jsonify(
            {
                "whatsapp": (settings.whatsapp if settings and settings.whatsapp else ""),
                "instagram": (settings.instagram if settings and settings.instagram else ""),
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port)
