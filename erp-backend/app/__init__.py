"""Flask factory do backend ERP EME Moveis."""
import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

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
    from app.api.bank_accounts_bp import bp as bank_accounts_bp
    from app.api.budget_bp import bp as budget_bp
    from app.api.calendar_bp import bp as calendar_bp
    from app.api.changelog_bp import bp as changelog_bp
    from app.api.clients_bp import bp as clients_bp
    from app.api.dashboard_bp import bp as dashboard_bp
    from app.api.financial_bp import bp as financial_bp
    from app.api.funnel_bp import bp as funnel_bp
    from app.api.goals_bp import bp as goals_bp
    from app.api.lead_options_bp import bp as lead_options_bp
    from app.api.projects_bp import bp as projects_bp
    from app.api.products_bp import bp as products_bp
    from app.api.reports_bp import bp as reports_bp
    from app.api.stock_bp import bp as stock_bp
    from app.api.suppliers_bp import bp as suppliers_bp
    from app.api.satisfaction_bp import bp as satisfaction_bp
    from app.api.posvenda_bp import bp as posvenda_bp
    from app.api.purchases_bp import bp as purchases_bp
    from app.api.tickets_bp import bp as tickets_bp
    from app.api.production_bp import bp as production_bp
    from app.api.partners_bp import bp as partners_bp
    from app.api.vendors_bp import bp as vendors_bp
    from app.api.proposals_bp import bp as proposals_bp
    from app.api.commissions_bp import bp as commissions_bp
    from app.api.whatsapp_bp import bp as whatsapp_bp

    for blueprint in (auth_bp, clients_bp, projects_bp, financial_bp, stock_bp, calendar_bp, funnel_bp, reports_bp, lead_options_bp, attachments_bp, products_bp, changelog_bp, suppliers_bp, satisfaction_bp, posvenda_bp, purchases_bp, budget_bp, tickets_bp, production_bp, bank_accounts_bp, partners_bp, vendors_bp, goals_bp, dashboard_bp, proposals_bp, commissions_bp, whatsapp_bp):
        app.register_blueprint(blueprint)

    @app.get("/api/health")
    def health():
        # max_upload_mb expoe o limite REAL para a tela nao exibir um numero
        # digitado a mao (foi assim que a tela passou a mentir "25 MB" enquanto
        # o nginx cortava em 1 MB).
        return jsonify({
            "ok": True,
            "app": "eme-moveis-erp",
            "max_upload_mb": max(1, int(app.config.get("MAX_CONTENT_LENGTH", 0)) // (1024 * 1024)),
        })

    @app.get("/")
    def root():
        return jsonify({"message": "EME Moveis ERP rodando"})

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_err):
        """413 em JSON com o limite REAL, para a tela nao chutar o numero.

        Sem isto o Flask devolve HTML cru e o front fica preso a um limite
        escrito na mao, que sai de sincronia com o backend.
        """
        limit_mb = max(1, int(app.config.get("MAX_CONTENT_LENGTH", 0)) // (1024 * 1024))
        return jsonify({
            "detail": f"Arquivo maior que o limite de {limit_mb} MB.",
            "limit_mb": limit_mb,
        }), 413

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
