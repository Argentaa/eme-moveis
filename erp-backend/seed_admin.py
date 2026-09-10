"""Cria o usuario ADMIN inicial via variaveis ADMIN_* (idempotente)."""
import os

from app import create_app
from app.auth import hash_password
from app.extensions import db
from app.models.models import User

USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin12345")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ememoveis.local")
NAME = os.environ.get("ADMIN_NAME", "Administrador")


def main():
    app = create_app(os.environ.get("APP_ENV", "prod"))
    with app.app_context():
        existing = db.session.query(User).filter_by(username=USERNAME).first()
        if existing:
            # Upsert: garante que o ADMIN do Dokploy sempre consegue logar,
            # mesmo quando o banco foi migrado do dump antigo (senha desconhecida).
            existing.password = hash_password(PASSWORD)
            existing.name = NAME
            existing.email = EMAIL
            existing.role = "ADMIN"
            db.session.commit()
            print(f"admin atualizado: {USERNAME}")
            return
        admin = User(
            username=USERNAME,
            name=NAME,
            email=EMAIL,
            role="ADMIN",
            password=hash_password(PASSWORD),
        )
        db.session.add(admin)
        db.session.commit()
        print(f"admin criado: {USERNAME}")


if __name__ == "__main__":
    main()
