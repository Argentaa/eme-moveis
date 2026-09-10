"""Auth JWT (PyJWT HS256) + bcrypt via Authorization Bearer."""
import functools
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import current_app, g, jsonify, request

from app.extensions import db


def _secret():
    return current_app.config.get("JWT_SECRET_KEY") or current_app.config.get(
        "SECRET_KEY", "dev-eme-moveis-change-me"
    )


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user) -> str:
    minutes = int(current_app.config.get("JWT_EXPIRE_MINUTES", 480))
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=["HS256"])


def token_required(roles=None):
    """Exige JWT valido. `roles`: lista opcional de roles permitidas."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from app.models.models import User

            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"detail": "Token ausente"}), 401
            token = auth[len("Bearer "):].strip()
            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"detail": "Token expirado"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"detail": "Token invalido"}), 401
            user = db.session.get(User, payload.get("sub"))
            if not user:
                return jsonify({"detail": "Usuario nao encontrado"}), 401
            if roles and user.role not in roles:
                return jsonify({"detail": "Permissao insuficiente"}), 403
            g.current_user = user
            g.token_payload = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator
