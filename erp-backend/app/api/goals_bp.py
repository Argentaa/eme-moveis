"""Planejamento comercial: metas de venda (sales_goals) e meta x realizado.

Separado de budget_bp, que trata orcamento de DESPESA por categoria.
Aqui e meta de RECEITA (geral, por vendedor ou por parceiro).

Realizado = soma do valor estimado dos clientes que entraram na ultima etapa do
funil dentro do periodo (clients.closed_at). closed_at passou a ser gravado no
update_client; clientes fechados ANTES disso ficam sem data e nao entram em
nenhum periodo — o campo `undated` do resumo diz quantos sao, para o numero ser
auditavel em vez de silenciosamente parcial.
"""
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.helpers import body_json, iso
from app.auth import token_required
from app.extensions import db
from app.models.models import Client, Funnel, FunnelColumn, SalesGoal, is_won_status, utcnow

bp = Blueprint("goals", __name__)

SCOPES = ("GERAL", "VENDEDOR", "PARCEIRO")
GOAL_FIELDS = ("year", "month", "scope", "user_id", "partner_id", "target_value")


def _fmt_brl(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(value):
    if value is None:
        return "--"
    return f"{value:.1f}%".replace(".", ",")


def _validate(data, partial=False):
    if not partial or "year" in data:
        try:
            y = int(data.get("year"))
        except (TypeError, ValueError):
            return jsonify({"detail": "year invalido"}), 400
        if y < 2000 or y > 2100:
            return jsonify({"detail": "year invalido"}), 400
    if not partial or "month" in data:
        m = data.get("month")
        if m not in (None, ""):
            try:
                mi = int(m)
            except (TypeError, ValueError):
                return jsonify({"detail": "month invalido"}), 400
            if mi < 1 or mi > 12:
                return jsonify({"detail": "month deve ser entre 1 e 12"}), 400
    if not partial or "scope" in data:
        scope = (data.get("scope") or "GERAL").strip().upper()
        if scope not in SCOPES:
            return jsonify({"detail": "scope deve ser GERAL, VENDEDOR ou PARCEIRO"}), 400
        if scope == "VENDEDOR" and not (data.get("user_id") or "").strip():
            return jsonify({"detail": "user_id e obrigatorio no escopo VENDEDOR"}), 400
        if scope == "PARCEIRO" and not (data.get("partner_id") or "").strip():
            return jsonify({"detail": "partner_id e obrigatorio no escopo PARCEIRO"}), 400
    if not partial or "target_value" in data:
        try:
            tv = float(data.get("target_value") or 0)
        except (TypeError, ValueError):
            return jsonify({"detail": "target_value invalido"}), 400
        if tv < 0:
            return jsonify({"detail": "target_value deve ser maior ou igual a 0"}), 400
    return None


def _apply(data, goal):
    for f in GOAL_FIELDS:
        if f not in data:
            continue
        v = data[f]
        if f in ("month", "user_id", "partner_id"):
            v = v if v not in (None, "") else None
            if f == "month" and v is not None:
                v = int(v)
        elif f == "year":
            v = int(v)
        elif f == "target_value":
            v = float(v or 0)
        elif f == "scope":
            v = (v or "GERAL").strip().upper()
        setattr(goal, f, v)


def _last_column_key(funnel_id):
    """Chave da ultima coluna do funil (a etapa de venda fechada)."""
    col = (db.session.query(FunnelColumn)
           .filter_by(funnel_id=funnel_id)
           .order_by(FunnelColumn.position.desc())
           .first())
    return col.column_key if col else None


@bp.get("/api/goals")
@token_required()
def list_goals():
    q = db.session.query(SalesGoal)
    year = request.args.get("year")
    month = request.args.get("month")
    scope = request.args.get("scope")
    if year:
        try:
            q = q.filter(SalesGoal.year == int(year))
        except (TypeError, ValueError):
            return jsonify({"detail": "year invalido"}), 400
    if month:
        try:
            q = q.filter(SalesGoal.month == int(month))
        except (TypeError, ValueError):
            return jsonify({"detail": "month invalido"}), 400
    if scope:
        q = q.filter(SalesGoal.scope == scope.strip().upper())
    rows = q.order_by(SalesGoal.year.desc(), SalesGoal.scope).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/goals")
@token_required(roles=["ADMIN", "GERENTE"])
def create_goal():
    data = body_json()
    err = _validate(data)
    if err:
        return err
    goal = SalesGoal()
    _apply(data, goal)
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201


@bp.put("/api/goals/<goal_id>")
@token_required(roles=["ADMIN", "GERENTE"])
def update_goal(goal_id):
    goal = db.session.get(SalesGoal, goal_id)
    if not goal:
        return jsonify({"detail": "Meta nao encontrada"}), 404
    data = body_json()
    err = _validate(data, partial=True)
    if err:
        return err
    _apply(data, goal)
    db.session.commit()
    return jsonify(goal.to_dict())


@bp.delete("/api/goals/<goal_id>")
@token_required(roles=["ADMIN", "GERENTE"])
def delete_goal(goal_id):
    goal = db.session.get(SalesGoal, goal_id)
    if not goal:
        return jsonify({"detail": "Meta nao encontrada"}), 404
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/goals/summary")
@token_required()
def summary():
    """Meta x realizado do periodo.

    target: metas do mes quando existirem; senao a meta do ano (month NULL).
    achieved: valor estimado dos clientes fechados dentro do periodo.
    """
    today = date.today()
    try:
        year = int(request.args.get("year") or today.year)
    except (TypeError, ValueError):
        return jsonify({"detail": "year invalido"}), 400
    if year < 2000 or year > 2100:
        return jsonify({"detail": "year invalido"}), 400

    month = request.args.get("month")
    if month in (None, ""):
        month = None
    else:
        try:
            month = int(month)
        except (TypeError, ValueError):
            return jsonify({"detail": "month invalido"}), 400
        if month < 1 or month > 12:
            return jsonify({"detail": "month deve ser entre 1 e 12"}), 400

    scope = (request.args.get("scope") or "GERAL").strip().upper()
    if scope not in SCOPES:
        return jsonify({"detail": "scope invalido"}), 400

    def _goals(month_filter):
        q = db.session.query(SalesGoal).filter(
            SalesGoal.year == year,
            SalesGoal.scope == scope,
        )
        q = (q.filter(SalesGoal.month == month_filter) if month_filter is not None
             else q.filter(SalesGoal.month.is_(None)))
        return q.all()

    target = 0.0
    target_basis = "ano"
    if month is not None:
        month_goals = _goals(month)
        if month_goals:
            target = sum(float(g.target_value or 0) for g in month_goals)
            target_basis = "mes"
        else:
            target = sum(float(g.target_value or 0) for g in _goals(None))
    else:
        target = sum(float(g.target_value or 0) for g in _goals(None))

    if month is not None:
        start = datetime(year, month, 1)
        end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    else:
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)

    closed = db.session.query(Client).filter(
        Client.closed_at.isnot(None),
        Client.closed_at >= start,
        Client.closed_at < end,
    ).all()
    achieved = sum(float(c.estimated_value or 0) for c in closed)

    # Clientes em etapa de VENDA GANHA sem data: fechados antes de closed_at
    # existir, ou em funil com nome proprio. Contados a parte para o resumo
    # avisar que a meta esta subestimada, em vez de somar errado.
    undated = 0
    for funnel in db.session.query(Funnel).filter(Funnel.kind == "CRM").all():
        last_key = _last_column_key(funnel.id)
        won_keys = [
            c.column_key
            for c in db.session.query(FunnelColumn).filter_by(funnel_id=funnel.id).all()
            if is_won_status(c.column_key, last_key)
        ]
        if not won_keys:
            continue
        undated += db.session.query(Client).filter(
            Client.funnel_id == funnel.id,
            Client.funnel_status.in_(won_keys),
            Client.closed_at.is_(None),
        ).count()

    remaining = target - achieved
    percent = (achieved / target * 100) if target > 0 else None
    return {
        "year": year,
        "month": month,
        "scope": scope,
        "target": _fmt_brl(target),
        "achieved": _fmt_brl(achieved),
        "remaining": _fmt_brl(remaining),
        "percent": _fmt_pct(percent),
        "deals_closed": len(closed),
        "undated": undated,
        "target_basis": target_basis,
        "basis": "valor estimado dos clientes fechados no periodo",
        "generated_at": iso(utcnow()),
    }
