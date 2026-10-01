"""Plano de contas: categorias DRE e contas (importadas do sistema legado).

GET    /api/account-plan/categories       lista categorias (+ contagem de contas)
POST   /api/account-plan/categories       cria categoria (ADMIN/GERENTE)
PUT    /api/account-plan/categories/<id>  edita categoria (ADMIN/GERENTE)
DELETE /api/account-plan/categories/<id>  remove categoria (ADMIN/GERENTE; 400 se tiver contas)
GET    /api/account-plan                  lista contas (agrupadas por categoria)
POST   /api/account-plan                  cria conta (ADMIN/GERENTE)
PUT    /api/account-plan/<id>             edita conta (ADMIN/GERENTE)
DELETE /api/account-plan/<id>             remove conta (ADMIN/GERENTE; com guard de lancamento)
POST   /api/account-plan/reload-seed      re-semeia o padrao do legado se o banco estiver vazio (seed)

O campo `financial_records.account_plan` continua um texto livre; o grupo
do DRE e definido aqui pelas contas cadastradas.
"""
import re

from flask import Blueprint, g, jsonify, request

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    AccountCategory,
    AccountPlan,
    FinancialRecord,
    ensure_default_account_plan,
)

bp = Blueprint("account_plan", __name__)

WRITE_ROLES = ["ADMIN", "GERENTE"]

CAT_FIELDS = ("code", "description", "indicator", "dre_range")
PLAN_FIELDS = ("code", "structured_code", "description", "category_id")


def _can_write():
    role = getattr(g, "current_user", None) and g.current_user.role
    return role in WRITE_ROLES


def _norm_code(raw):
    try:
        code = int(raw)
    except (TypeError, ValueError):
        return None
    return code if code > 0 else None


def _parse_structured(raw):
    if not raw:
        return None
    s = str(raw).strip()
    if not re.fullmatch(r"\d{1,2}\.\d{1,2}", s):
        return None
    return s


def _category_payload(cat):
    d = cat.to_dict()
    d["plan_count"] = db.session.query(AccountPlan).filter_by(category_id=cat.id).count()
    return d


# ── Categorias ────────────────────────────────────────────────

@bp.get("/api/account-plan/categories")
@token_required()
def list_categories():
    rows = db.session.query(AccountCategory).order_by(AccountCategory.code).all()
    return jsonify([_category_payload(c) for c in rows])


@bp.post("/api/account-plan/categories")
@token_required(roles=WRITE_ROLES)
def create_category():
    data = body_json()
    description = (data.get("description") or "").strip()
    if not description:
        return jsonify({"detail": "description e obrigatoria"}), 400
    code = _norm_code(data.get("code"))
    if code is None:
        return jsonify({"detail": "code deve ser um numero maior que zero"}), 400
    if db.session.query(AccountCategory).filter_by(code=code).first():
        return jsonify({"detail": "Ja existe categoria com este codigo"}), 400
    indicator = (data.get("indicator") or "DEBITO").strip().upper()
    if indicator not in ("CREDITO", "DEBITO"):
        return jsonify({"detail": "indicator deve ser CREDITO ou DEBITO"}), 400
    cat = AccountCategory(
        code=code,
        description=description,
        indicator=indicator,
        dre_range=(data.get("dre_range") or "").strip(),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(_category_payload(cat)), 201


@bp.put("/api/account-plan/categories/<category_id>")
@token_required(roles=WRITE_ROLES)
def update_category(category_id):
    cat = db.session.get(AccountCategory, category_id)
    if not cat:
        return jsonify({"detail": "Categoria nao encontrada"}), 404
    data = body_json()
    if "code" in data:
        code = _norm_code(data.get("code"))
        if code is None:
            return jsonify({"detail": "code deve ser um numero maior que zero"}), 400
        dup = db.session.query(AccountCategory).filter(
            AccountCategory.code == code, AccountCategory.id != cat.id
        ).first()
        if dup:
            return jsonify({"detail": "Ja existe categoria com este codigo"}), 400
        cat.code = code
    if "description" in data:
        description = (data.get("description") or "").strip()
        if not description:
            return jsonify({"detail": "description nao pode ser vazia"}), 400
        cat.description = description
    if "indicator" in data:
        indicator = (data.get("indicator") or "").strip().upper()
        if indicator not in ("CREDITO", "DEBITO"):
            return jsonify({"detail": "indicator deve ser CREDITO ou DEBITO"}), 400
        cat.indicator = indicator
    if "dre_range" in data:
        cat.dre_range = (data.get("dre_range") or "").strip()
    db.session.commit()
    return jsonify(_category_payload(cat))


@bp.delete("/api/account-plan/categories/<category_id>")
@token_required(roles=WRITE_ROLES)
def delete_category(category_id):
    cat = db.session.get(AccountCategory, category_id)
    if not cat:
        return jsonify({"detail": "Categoria nao encontrada"}), 404
    n_plans = db.session.query(AccountPlan).filter_by(category_id=cat.id).count()
    if n_plans:
        return jsonify(
            {"detail": "Categoria possui %d conta(s); mova ou exclua as contas primeiro" % n_plans}
        ), 400
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"ok": True})


# ── Contas ────────────────────────────────────────────────────

@bp.get("/api/account-plan")
@token_required()
def list_plans():
    """Contas agrupadas por categoria (ordem oficial do legado: por categoria, depois codigo)."""
    cats = db.session.query(AccountCategory).order_by(AccountCategory.code).all()
    plans = (
        db.session.query(AccountPlan)
        .order_by(AccountPlan.code)
        .all()
    )
    grouped = []
    for cat in cats:
        grouped.append({
            "id": cat.id,
            "code": cat.code,
            "description": cat.description,
            "indicator": cat.indicator,
            "dre_range": cat.dre_range or "",
            "plans": [p.to_dict() for p in plans if p.category_id == cat.id],
        })
    return jsonify(grouped)


@bp.post("/api/account-plan")
@token_required(roles=WRITE_ROLES)
def create_plan():
    data = body_json()
    description = (data.get("description") or "").strip()
    if not description:
        return jsonify({"detail": "description e obrigatoria"}), 400
    structured = _parse_structured(data.get("structured_code"))
    if not structured:
        return jsonify({"detail": "structured_code deve seguir o formato X.Y (ex.: 4.2)"}), 400
    if db.session.query(AccountPlan).filter_by(structured_code=structured).first():
        return jsonify({"detail": "Ja existe conta com esse codigo estruturado"}), 400
    code = _norm_code(data.get("code"))
    if code is None:
        return jsonify({"detail": "code deve ser um numero maior que zero"}), 400
    if db.session.query(AccountPlan).filter_by(code=code).first():
        return jsonify({"detail": "Ja existe conta com esse codigo"}), 400
    cat = db.session.get(AccountCategory, data.get("category_id") or "")
    if not cat:
        return jsonify({"detail": "Categoria nao encontrada"}), 400
    plan = AccountPlan(
        code=code,
        structured_code=structured,
        description=description,
        category_id=cat.id,
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify(plan.to_dict()), 201


@bp.put("/api/account-plan/<plan_id>")
@token_required(roles=WRITE_ROLES)
def update_plan(plan_id):
    plan = db.session.get(AccountPlan, plan_id)
    if not plan:
        return jsonify({"detail": "Conta nao encontrada"}), 404
    data = body_json()
    if "structured_code" in data:
        structured = _parse_structured(data.get("structured_code"))
        if not structured:
            return jsonify({"detail": "structured_code deve seguir o formato X.Y (ex.: 4.2)"}), 400
        dup = db.session.query(AccountPlan).filter(
            AccountPlan.structured_code == structured, AccountPlan.id != plan.id
        ).first()
        if dup:
            return jsonify({"detail": "Ja existe conta com esse codigo estruturado"}), 400
        plan.structured_code = structured
    if "code" in data:
        code = _norm_code(data.get("code"))
        if code is None:
            return jsonify({"detail": "code deve ser um numero maior que zero"}), 400
        dup = db.session.query(AccountPlan).filter(
            AccountPlan.code == code, AccountPlan.id != plan.id
        ).first()
        if dup:
            return jsonify({"detail": "Ja existe conta com esse codigo"}), 400
        plan.code = code
    if "description" in data:
        description = (data.get("description") or "").strip()
        if not description:
            return jsonify({"detail": "description nao pode ser vazia"}), 400
        plan.description = description
    if "category_id" in data:
        cat = db.session.get(AccountCategory, data.get("category_id") or "")
        if not cat:
            return jsonify({"detail": "Categoria nao encontrada"}), 400
        plan.category_id = cat.id
    db.session.commit()
    return jsonify(plan.to_dict())


@bp.delete("/api/account-plan/<plan_id>")
@token_required(roles=WRITE_ROLES)
def delete_plan(plan_id):
    plan = db.session.get(AccountPlan, plan_id)
    if not plan:
        return jsonify({"detail": "Conta nao encontrada"}), 404
    used = db.session.query(FinancialRecord).filter(
        FinancialRecord.account_plan == plan.structured_code
    ).first()
    if used:
        return jsonify(
            {"detail": "Conta ja usada em lancamento(s); remova o vinculo antes de excluir"}
        ), 400
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/api/account-plan/reload-seed")
@token_required(roles=WRITE_ROLES)
def reload_seed():
    """Re-semeia o padrao oficial do legado se faltar alguma categoria/conta."""
    ensure_default_account_plan()
    return jsonify({"ok": True})