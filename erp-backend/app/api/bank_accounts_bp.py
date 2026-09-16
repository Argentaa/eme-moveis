"""CRUD /api/bank-accounts (+ /overview, /<id>/balance)."""
from datetime import date, datetime, timezone

from flask import Blueprint, g, jsonify
from sqlalchemy import func

from app.auth import token_required
from app.extensions import db
from app.helpers import body_json, iso, num, parse_date
from app.models.models import BankAccount, FinancialRecord

bp = Blueprint("bank_accounts", __name__)

ACCOUNT_TYPES = {"CORRENTE", "POUPANCA", "APLICACAO"}


def _creator():
    return g.current_user.username if hasattr(g, "current_user") else ""


def _validate_account_type(v):
    if v not in ACCOUNT_TYPES:
        return jsonify({"detail": "account_type invalido"}), 400
    return None


def _sum_amount(query_filters):
    try:
        val = db.session.query(func.coalesce(func.sum(FinancialRecord.amount), 0)).filter(*query_filters).scalar()
        return float(val or 0)
    except Exception:
        return 0.0


@bp.get("/api/bank-accounts")
@token_required()
def list_accounts():
    rows = db.session.query(BankAccount).order_by(BankAccount.name).all()
    return jsonify([a.to_dict() for a in rows])


@bp.get("/api/bank-accounts/overview")
@token_required()
def overview():
    active_accounts = db.session.query(BankAccount).filter(BankAccount.active.is_(True)).order_by(BankAccount.name).all()
    total_balance = 0.0
    total_projected = 0.0
    for acc in active_accounts:
        try:
            cur = float(acc.current_balance)
        except Exception:
            cur = float(acc.opening_balance or 0)
        total_balance += cur
        # projected per account
        entradas_pend = _sum_amount([FinancialRecord.bank_account_id == acc.id, FinancialRecord.type == "ENTRADA", FinancialRecord.status == "PENDENTE"])
        saidas_pend = _sum_amount([FinancialRecord.bank_account_id == acc.id, FinancialRecord.type == "SAIDA", FinancialRecord.status == "PENDENTE"])
        proj = cur + entradas_pend - saidas_pend
        total_projected += proj
    return jsonify({"total_balance": total_balance, "total_projected": total_projected, "accounts": [a.to_dict() for a in active_accounts]})


@bp.get("/api/bank-accounts/<account_id>")
@token_required()
def get_account(account_id):
    acc = db.session.get(BankAccount, account_id)
    if not acc:
        return jsonify({"detail": "Conta bancaria nao encontrada"}), 404
    return jsonify(acc.to_dict())


@bp.post("/api/bank-accounts")
@token_required()
def create_account():
    data = body_json()
    name = (data.get("name") or "").strip() if isinstance(data.get("name"), str) else ""
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400

    account_type = data.get("account_type")
    if account_type not in (None, ""):
        if not isinstance(account_type, str):
            return jsonify({"detail": "account_type invalido"}), 400
        account_type = account_type.strip().upper()
        if account_type not in ACCOUNT_TYPES:
            return jsonify({"detail": "account_type invalido"}), 400
    else:
        account_type = "CORRENTE"

    # opening_balance
    opening_balance = 0
    if "opening_balance" in data and data.get("opening_balance") not in (None, ""):
        try:
            ob = num(data.get("opening_balance"))
            if ob is None:
                return jsonify({"detail": "opening_balance invalido"}), 400
            fv = float(ob)
            import math

            if math.isnan(fv) or math.isinf(fv):
                return jsonify({"detail": "opening_balance invalido"}), 400
            if fv < 0:
                return jsonify({"detail": "opening_balance deve ser maior ou igual a zero"}), 400
            opening_balance = fv
        except (TypeError, ValueError):
            return jsonify({"detail": "opening_balance invalido"}), 400

    # low_balance_threshold
    low_balance_threshold = None
    if "low_balance_threshold" in data and data.get("low_balance_threshold") not in (None, ""):
        try:
            lb = num(data.get("low_balance_threshold"))
            if lb is None:
                return jsonify({"detail": "low_balance_threshold invalido"}), 400
            fv = float(lb)
            import math

            if math.isnan(fv) or math.isinf(fv):
                return jsonify({"detail": "low_balance_threshold invalido"}), 400
            if fv < 0:
                return jsonify({"detail": "low_balance_threshold deve ser maior ou igual a zero"}), 400
            low_balance_threshold = fv
        except (TypeError, ValueError):
            return jsonify({"detail": "low_balance_threshold invalido"}), 400

    bank = (data.get("bank") or "").strip() if isinstance(data.get("bank"), str) else ""
    agency = (data.get("agency") or "").strip() if isinstance(data.get("agency"), str) else ""
    account_number = (data.get("account_number") or "").strip() if isinstance(data.get("account_number"), str) else ""
    notes = (data.get("notes") or "").strip() if isinstance(data.get("notes"), str) else ""

    active = data.get("active")
    if active is None:
        active = True
    else:
        # accept bool or truthy str
        if isinstance(active, bool):
            pass
        elif isinstance(active, str):
            active = active.lower() in ("true", "1", "sim", "yes")
        else:
            active = bool(active)

    opening_date = parse_date(data.get("opening_date")) if data.get("opening_date") not in (None, "") else None

    acc = BankAccount(
        name=name,
        bank=bank,
        agency=agency,
        account_number=account_number,
        account_type=account_type,
        opening_balance=opening_balance,
        opening_date=opening_date,
        active=bool(active),
        low_balance_threshold=low_balance_threshold,
        notes=notes,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(acc)
    db.session.commit()
    return jsonify(acc.to_dict()), 201


@bp.put("/api/bank-accounts/<account_id>")
@token_required()
def update_account(account_id):
    acc = db.session.get(BankAccount, account_id)
    if not acc:
        return jsonify({"detail": "Conta bancaria nao encontrada"}), 404
    data = body_json()

    if "name" in data:
        raw = data.get("name")
        if not isinstance(raw, str) or not raw.strip():
            return jsonify({"detail": "name e obrigatorio"}), 400
        acc.name = raw.strip()

    if "account_type" in data:
        raw = data.get("account_type")
        if raw not in (None, ""):
            if not isinstance(raw, str):
                return jsonify({"detail": "account_type invalido"}), 400
            v = raw.strip().upper()
            if v not in ACCOUNT_TYPES:
                return jsonify({"detail": "account_type invalido"}), 400
            acc.account_type = v

    if "opening_balance" in data:
        raw = data.get("opening_balance")
        if raw in (None, ""):
            acc.opening_balance = 0
        else:
            try:
                ob = num(raw)
                if ob is None:
                    return jsonify({"detail": "opening_balance invalido"}), 400
                fv = float(ob)
                import math

                if math.isnan(fv) or math.isinf(fv):
                    return jsonify({"detail": "opening_balance invalido"}), 400
                if fv < 0:
                    return jsonify({"detail": "opening_balance deve ser maior ou igual a zero"}), 400
                acc.opening_balance = fv
            except (TypeError, ValueError):
                return jsonify({"detail": "opening_balance invalido"}), 400

    if "low_balance_threshold" in data:
        raw = data.get("low_balance_threshold")
        if raw in (None, ""):
            acc.low_balance_threshold = None
        else:
            try:
                lb = num(raw)
                if lb is None:
                    return jsonify({"detail": "low_balance_threshold invalido"}), 400
                fv = float(lb)
                import math

                if math.isnan(fv) or math.isinf(fv):
                    return jsonify({"detail": "low_balance_threshold invalido"}), 400
                if fv < 0:
                    return jsonify({"detail": "low_balance_threshold deve ser maior ou igual a zero"}), 400
                acc.low_balance_threshold = fv
            except (TypeError, ValueError):
                return jsonify({"detail": "low_balance_threshold invalido"}), 400

    if "bank" in data:
        raw = data.get("bank")
        acc.bank = (raw or "").strip() if isinstance(raw, str) else ""
    if "agency" in data:
        raw = data.get("agency")
        acc.agency = (raw or "").strip() if isinstance(raw, str) else ""
    if "account_number" in data:
        raw = data.get("account_number")
        acc.account_number = (raw or "").strip() if isinstance(raw, str) else ""
    if "notes" in data:
        raw = data.get("notes")
        acc.notes = (raw or "").strip() if isinstance(raw, str) else ""
    if "active" in data:
        raw = data.get("active")
        if isinstance(raw, bool):
            acc.active = raw
        elif isinstance(raw, str):
            acc.active = raw.lower() in ("true", "1", "sim", "yes")
        else:
            acc.active = bool(raw)
    if "opening_date" in data:
        raw = data.get("opening_date")
        if raw in (None, ""):
            acc.opening_date = None
        else:
            try:
                acc.opening_date = parse_date(raw)
            except Exception:
                return jsonify({"detail": "opening_date invalida"}), 400

    db.session.commit()
    return jsonify(acc.to_dict())


@bp.delete("/api/bank-accounts/<account_id>")
@token_required()
def delete_account(account_id):
    acc = db.session.get(BankAccount, account_id)
    if not acc:
        return jsonify({"detail": "Conta bancaria nao encontrada"}), 404
    # bloqueia se houver lancamentos vinculados
    exists_linked = db.session.query(FinancialRecord).filter(FinancialRecord.bank_account_id == account_id).first() is not None
    if exists_linked:
        return jsonify({"detail": "Conta em uso por lancamentos"}), 400
    db.session.delete(acc)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/bank-accounts/<account_id>/balance")
@token_required()
def balance_account(account_id):
    acc = db.session.get(BankAccount, account_id)
    if not acc:
        return jsonify({"detail": "Conta bancaria nao encontrada"}), 404
    try:
        current = float(acc.current_balance)
    except Exception:
        current = float(acc.opening_balance or 0)

    entradas_pagas = _sum_amount([FinancialRecord.bank_account_id == acc.id, FinancialRecord.type == "ENTRADA", FinancialRecord.status == "PAGO"])
    saidas_pagas = _sum_amount([FinancialRecord.bank_account_id == acc.id, FinancialRecord.type == "SAIDA", FinancialRecord.status == "PAGO"])
    entradas_pend = _sum_amount([FinancialRecord.bank_account_id == acc.id, FinancialRecord.type == "ENTRADA", FinancialRecord.status == "PENDENTE"])
    saidas_pend = _sum_amount([FinancialRecord.bank_account_id == acc.id, FinancialRecord.type == "SAIDA", FinancialRecord.status == "PENDENTE"])

    projected = current + entradas_pend - saidas_pend

    return jsonify(
        {
            "id": acc.id,
            "name": acc.name,
            "current_balance": current,
            "projected_balance": projected,
            "opening_balance": num(acc.opening_balance),
            "entradas_pagas": entradas_pagas,
            "saidas_pagas": saidas_pagas,
            "entradas_pendentes": entradas_pend,
            "saidas_pendentes": saidas_pend,
        }
    )
