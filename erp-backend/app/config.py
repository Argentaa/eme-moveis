"""Configuracao do backend ERP EME Moveis (Flask factory)."""
import os


def _database_uri(default_sqlite="sqlite:///eme_moveis.db"):
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return default_sqlite
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _int_env(*names, default):
    for n in names:
        v = os.environ.get(n)
        if v not in (None, ""):
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-eme-moveis-change-me")
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", os.environ.get("SECRET_KEY", "dev-eme-moveis-change-me")
    )
    # Aliases: compose usa ACCESS_TOKEN_EXPIRE_MINUTES / ERP_JWT_MINUTES,
    # .env usa JWT_EXPIRE_MINUTES. Aceita os tres.
    JWT_EXPIRE_MINUTES = _int_env(
        "JWT_EXPIRE_MINUTES",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "ERP_JWT_MINUTES",
        default=480,
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = _database_uri("sqlite:///eme_moveis_dev.db")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    JWT_SECRET_KEY = "test-secret-com-mais-de-32-bytes-para-hmac-sha256-ok"
    JWT_EXPIRE_MINUTES = 60


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = _database_uri("sqlite:///eme_moveis.db")


configs = {"dev": DevConfig, "test": TestConfig, "prod": ProdConfig}
