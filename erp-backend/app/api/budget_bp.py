"""Planejamento orcamentario: metas por categoria/ano/mes e analise orcado x realizado."""
from datetime import date

from flask import Blueprint, jsonify, request

from sqlalchemy import or_

from app.helpers import body_json, iso
from app.auth import token_required
from app.extensions import db
from app.models.models import BudgetGoal, FinancialRecord

bp = Blueprint("budget", __name__)

GOAL_FIELDS = ("year", "month", "category", "target_value")


def _fmt_brl(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _validate_goal(data, partial=False):
    if not partial or "year" in data:
        try:
            y = int(data.get("year"))
        except (TypeError, ValueError):
            return jsonify({"detail": "year invalido"}), 400
        if y < 2000 or y > 2100:
            return jsonify({"detail": "year invalido"}), 400
    if partial and "month" not in data:
        return None
    m = data.get("month")
    if m not in (None, ""):
        try:
            mi = int(m)
        except (TypeError, ValueError):
            return jsonify({"detail": "month invalido"}), 400
        if mi < 1 or mi > 12:
            return jsonify({"detail": "month deve ser entre 1 e 12"}), 400
    if not partial or "target_value" in data:
        try:
            tv = float(data.get("target_value") or 0)
        except (TypeError, ValueError):
            return jsonify({"detail": "target_value invalido"}), 400
        if tv < 0:
            return jsonify({"detail": "target_value deve ser maior ou igual a 0"}), 400
    if not partial or "category" in data:
        cat = (data.get("category") or "").strip()
        if not cat:
            return jsonify({"detail": "category e obrigatoria"}), 400
    return None


def _apply_goal(data, goal):
    for f in GOAL_FIELDS:
        if f not in data:
            continue
        v = data[f]
        if f == "month" and v in (None, ""):
            v = None
        elif f == "month":
            v = int(v)
        elif f in ("year",):
            v = int(v)
        elif f == "target_value":
            v = float(v or 0)
        setattr(goal, f, v)


@bp.get("/api/budget/goals")
@token_required()
def list_goals():
    q = db.session.query(BudgetGoal)
    year = request.args.get("year")
    month = request.args.get("month")
    if year:
        try:
            q = q.filter(BudgetGoal.year == int(year))
        except (TypeError, ValueError):
            return jsonify({"detail": "year invalido"}), 400
    if month:
        try:
            q = q.filter(BudgetGoal.month == int(month))
        except (TypeError, ValueError):
            return jsonify({"detail": "month invalido"}), 400
    rows = q.order_by(BudgetGoal.year.desc(), BudgetGoal.category).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/budget/goals")
@token_required()
def create_goal():
    data = body_json()
    err = _validate_goal(data)
    if err:
        return err
    goal = BudgetGoal()
    _apply_goal(data, goal)
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201


@bp.put("/api/budget/goals/<goal_id>")
@token_required()
def update_goal(goal_id):
    goal = db.session.get(BudgetGoal, goal_id)
    if not goal:
        return jsonify({"detail": "Meta nao encontrada"}), 404
    data = body_json()
    err = _validate_goal(data, partial=True)
    if err:
        return err
    _apply_goal(data, goal)
    db.session.commit()
    return jsonify(goal.to_dict())


@bp.delete("/api/budget/goals/<goal_id>")
@token_required()
def delete_goal(goal_id):
    goal = db.session.get(BudgetGoal, goal_id)
    if not goal:
        return jsonify({"detail": "Meta nao encontrada"}), 404
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/budget/analysis")
@token_required()
def analysis():
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

    q = db.session.query(BudgetGoal).filter(BudgetGoal.year == year)
    if month:
        q = q.filter(or_(BudgetGoal.month == month, BudgetGoal.month.is_(None)))
    else:
        q = q.filter(BudgetGoal.month.is_(None))
    goals = q.all()

    if month:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    else:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)

    recs = db.session.query(FinancialRecord).filter(
        FinancialRecord.status == "PAGO",
        FinancialRecord.date >= start,
        FinancialRecord.date < end,
    ).all()
    realized = {}
    for r in recs:
        cat = r.category or "Sem categoria"
        realized[cat] = realized.get(cat, 0.0) + float(r.amount or 0)

    budget_map = {}
    for g in goals:
        budget_map[g.category] = budget_map.get(g.category, 0.0) + float(g.target_value or 0)

    rows = []
    total_budget = 0.0
    total_realized = 0.0
    for cat in sorted(set(list(budget_map.keys()) + list(realized.keys()))):
        b = budget_map.get(cat, 0.0)
        a = realized.get(cat, 0.0)
        diff = b - a
        pct = (a / b * 100) if b > 0 else None
        total_budget += b
        total_realized += a
        rows.append({
            "category": cat,
            "budget": _fmt_brl(b),
            "actual": _fmt_brl(a),
            "difference": _fmt_brl(diff),
            "percentage": (f"{pct:.1f}%".replace(".", ",")) if pct is not None else "--",
            "_budget": round(b, 2),
            "_actual": round(a, 2),
        })

    total_diff = total_budget - total_realized
    total_pct = (total_realized / total_budget * 100) if total_budget > 0 else None
    return {
        "title": "Orçamento x Realizado",
        "generated_at": iso(date.today()),
        "period": {"year": year, "month": month},
        "summary": [
            {"label": "Orçado Total", "value": _fmt_brl(total_budget), "tone": "neutral"},
            {"label": "Realizado Total", "value": _fmt_brl(total_realized), "tone": "positive"},
            {"label": "Diferença", "value": _fmt_brl(total_diff),
             "tone": "positive" if total_diff >= 0 else "negative"},
            {"label": "Realizado %", "value": (f"{total_pct:.1f}%".replace(".", ",")) if total_pct is not None else "--", "tone": "neutral"},
        ],
        "columns": [
            {"key": "category", "label": "Categoria"},
            {"key": "budget", "label": "Orçado"},
            {"key": "actual", "label": "Realizado"},
            {"key": "difference", "label": "Diferença"},
            {"key": "percentage", "label": "% Realizado"},
        ],
        "rows": rows,
    }