"""Flask factory do backend ERP EME Moveis."""
import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.config import configs
from app.extensions import db


def create_app(config_name=None):
    config_name = config_name or os.environ.get("APP_ENV", "dev")
    app = Flask(__name__)
    app.config.from_object(configs.get(config_name, configs["dev"]))
    app.url_map.strict_slashes = False

    origins = [o.strip() for o in str(app.config.get("CORS_ORIGINS", "*")).split(",")]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    db.init_app(app)

    from app.api.auth_bp import bp as auth_bp
    from app.api.attachments_bp import bp as attachments_bp
    from app.api.budget_bp import bp as budget_bp
    from app.api.calendar_bp import bp as calendar_bp
    from app.api.changelog_bp import bp as changelog_bp
    from app.api.clients_bp import bp as clients_bp
    from app.api.financial_bp import bp as financial_bp
    from app.api.funnel_bp import bp as funnel_bp
    from app.api.lead_options_bp import bp as lead_options_bp
    from app.api.projects_bp import bp as projects_bp
    from app.api.products_bp import bp as products_bp
    from app.api.reports_bp import bp as reports_bp
    from app.api.stock_bp import bp as stock_bp
    from app.api.suppliers_bp import bp as suppliers_bp

    for blueprint in (auth_bp, clients_bp, projects_bp, financial_bp, stock_bp, calendar_bp, funnel_bp, reports_bp, lead_options_bp, attachments_bp, products_bp, changelog_bp, suppliers_bp, budget_bp):
        app.register_blueprint(blueprint)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "app": "eme-moveis-erp"})

    @app.get("/")
    def root():
        return jsonify({"message": "EME Moveis ERP rodando"})

    with app.app_context():
        from app import models as _models  # noqa: F401
        from app.models.models import ensure_default_funnel_columns, ensure_default_funnels

        db.create_all()
        try:
            ensure_default_funnels()
        except Exception:
            pass
        try:
            ensure_default_funnel_columns()
        except Exception:
            pass

        from app.models.models import ensure_default_campaigns, ensure_default_changelog, ensure_default_lead_sources
        try:
            ensure_default_lead_sources()
        except Exception:
            pass
        try:
            ensure_default_campaigns()
        except Exception:
            pass
        try:
            ensure_default_changelog()
        except Exception:
            pass

    return app
