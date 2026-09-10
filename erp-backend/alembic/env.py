"""Alembic env funcional: usa DATABASE_URL (postgres) com fallback sqlite."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging.config import fileConfig

from alembic import context

from app import create_app
from app.extensions import db
import app.models  # noqa: F401

config = context.config
if config.config_file_name:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

target_metadata = db.Model.metadata


def get_url():
    url = os.environ.get("DATABASE_URL", "")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    try:
        app = create_app(os.environ.get("APP_ENV", "dev"))
        return app.config["SQLALCHEMY_DATABASE_URI"]
    except Exception:
        return "sqlite:///eme_moveis_dev.db"


def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    from sqlalchemy import engine_from_config

    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = get_url()
    engine = engine_from_config(cfg, prefix="sqlalchemy.")
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
