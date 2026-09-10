"""Autenticação JWT HS256 (expiração 8h) via SITE_JWT_SECRET. Sem token fixo."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import jsonify, request

JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(hours=8)


def _secret() -> str:
    secret = os.environ.get("SITE_JWT_SECRET", "")
    if not secret:
        raise RuntimeError("SITE_JWT_SECRET não configurado")
    return secret


def create_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + JWT_EXPIRY,
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])


def require_auth(fn):
    """Middleware: exige `Authorization: Bearer <JWT>` válido."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Não autorizado. Faça login novamente."}), 401
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"error": "Não autorizado. Faça login novamente."}), 401
        try:
            claims = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token inválido ou expirado."}), 403
        except Exception:
            return jsonify({"error": "Token inválido ou expirado."}), 403
        request.auth_claims = claims  # type: ignore[attr-defined]
        return fn(*args, **kwargs)

    return wrapper
