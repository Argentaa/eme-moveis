"""POST /api/auth/login, GET /api/auth/me, CRUD /api/auth/users."""
from flask import Blueprint, g, jsonify

from app.helpers import body_json
from app.auth import check_password, create_token, hash_password, token_required
from app.extensions import db
from app.models.models import User

bp = Blueprint("auth", __name__)

VALID_ROLES = {"ADMIN", "GERENTE", "ESTOQUE", "PROJETISTA"}


@bp.post("/api/auth/login")
def login():
    data = body_json()
    user = db.session.query(User).filter_by(username=(data.get("username") or "").strip()).first()
    if not user or not check_password(data.get("password") or "", user.password or ""):
        return jsonify({"detail": "Usuario ou senha invalidos"}), 401
    return jsonify({"token": create_token(user), "user": user.to_dict()})


@bp.get("/api/auth/me")
@token_required()
def me():
    return jsonify(g.current_user.to_dict())


@bp.get("/api/auth/users")
@token_required(roles=["ADMIN"])
def list_users():
    users = db.session.query(User).order_by(User.name).all()
    return jsonify([u.to_dict() for u in users])


@bp.post("/api/auth/users")
@token_required(roles=["ADMIN"])
def create_user():
    data = body_json()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "ESTOQUE").upper()
    if not username or not email or not password:
        return jsonify({"detail": "username, email e password sao obrigatorios"}), 400
    if len(password) < 8:
        return jsonify({"detail": "A senha deve ter no minimo 8 caracteres"}), 400
    if role not in VALID_ROLES:
        return jsonify({"detail": "Role invalida"}), 400
    if db.session.query(User).filter_by(username=username).first():
        return jsonify({"detail": "Username ja cadastrado"}), 400
    if db.session.query(User).filter_by(email=email).first():
        return jsonify({"detail": "Email ja cadastrado"}), 400
    user = User(
        username=username,
        name=data.get("name") or username,
        email=email,
        role=role,
        password=hash_password(password),
        avatar=data.get("avatar"),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@bp.put("/api/auth/users/<user_id>")
@token_required(roles=["ADMIN"])
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"detail": "Usuario nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        user.name = data["name"]
    if "email" in data and data["email"] != user.email:
        if db.session.query(User).filter(User.email == data["email"], User.id != user.id).first():
            return jsonify({"detail": "Email ja cadastrado"}), 400
        user.email = data["email"]
    if "username" in data and data["username"] != user.username:
        if db.session.query(User).filter(User.username == data["username"], User.id != user.id).first():
            return jsonify({"detail": "Username ja cadastrado"}), 400
        user.username = data["username"]
    if "avatar" in data:
        user.avatar = data["avatar"]
    if "role" in data and data["role"]:
        role = str(data["role"]).upper()
        if role not in VALID_ROLES:
            return jsonify({"detail": "Role invalida"}), 400
        user.role = role
    if data.get("password"):
        if len(data["password"]) < 8:
            return jsonify({"detail": "A senha deve ter no minimo 8 caracteres"}), 400
        user.password = hash_password(data["password"])
    db.session.commit()
    return jsonify(user.to_dict())


@bp.put("/api/auth/users/<user_id>/role")
@token_required(roles=["ADMIN"])
def update_user_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"detail": "Usuario nao encontrado"}), 404
    role = str(body_json().get("role") or "").upper()
    if role not in VALID_ROLES:
        return jsonify({"detail": "Role invalida"}), 400
    user.role = role
    db.session.commit()
    return jsonify(user.to_dict())


@bp.delete("/api/auth/users/<user_id>")
@token_required(roles=["ADMIN"])
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"detail": "Usuario nao encontrado"}), 404
    if user.id == g.current_user.id:
        return jsonify({"detail": "Nao e possivel excluir o proprio usuario"}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True})
