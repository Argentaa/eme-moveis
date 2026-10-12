"""Comissoes: regras (percentual + vigencia) e o calculo do periodo.

A comissao e uma REGRA aplicada sobre as vendas fechadas do periodo, nao um
valor congelado no momento da venda. Isso significa que mudar o percentual de um
vendedor hoje nao reescreve o que ja foi pago nos meses anteriores — recalcular
o mes passado continua dando o mesmo numero.

"Venda fechada" e exatamente a mesma definicao do planejamento comercial
(goals_bp): vendas geradas (Sale, por sale_date) + concluido pelo botao SEM
Sale (por clients.closed_at, sem duplicar: cliente com Sale nao entra aqui).
Se as duas telas usassem definicoes diferentes, a meta e a comissao contariam
historias diferentes sobre o mesmo mes. A base em Sale tambem preserva o
historico quando o cliente reabre nova negociacao no funil (as flags do
cliente sao limpas na reabertura, mas a Sale permanece).

Atribuicao:
  - vendedor -> `sales.seller_id` (venda gerada) ou `clients.seller_id`
    (concluido pelo botao sem Sale)
  - parceiro -> `sales.partner_id` ou `clients.partner_id`
Vendas fechadas sem vendedor aparecem em `sem_atribuicao` (vendedor), para o
numero nao parecer completo quando nao e.
"""
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.helpers import body_json, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import Client, CommissionRule, Partner, Sale, User, utcnow

bp = Blueprint("commissions", __name__)


def _periodo():
    """(start, end) do periodo pedido; month ausente = ano inteiro."""
    hoje = date.today()
    try:
        year = int(request.args.get("year") or hoje.year)
    except (TypeError, ValueError):
        return None, None, (jsonify({"detail": "year invalido"}), 400)
    if year < 2000 or year > 2100:
        return None, None, (jsonify({"detail": "year invalido"}), 400)

    raw_month = request.args.get("month")
    month = None
    if raw_month not in (None, ""):
        try:
            month = int(raw_month)
        except (TypeError, ValueError):
            return None, None, (jsonify({"detail": "month invalido"}), 400)
        if month < 1 or month > 12:
            return None, None, (jsonify({"detail": "month invalido"}), 400)

    if month is not None:
        start = datetime(year, month, 1)
        end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    else:
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
    return start, end, None


def _regra_vale(rule, start, end):
    """A regra vale no periodo? Vigencia nula = sempre."""
    if not rule.active:
        return False
    if rule.valid_from and rule.valid_from >= end.date():
        return False
    if rule.valid_until and rule.valid_until < start.date():
        return False
    return True


@bp.get("/api/commissions")
@token_required()
def commissions():
    start, end, erro = _periodo()
    if erro:
        return erro

    # Fonte unica = mesma do planejamento (goals_bp): vendas geradas contam
    # por Sale.sale_date; concluido pelo botao SEM Sale conta por closed_at.
    # Cliente com qualquer Sale nao entra pela flag (evita duplicar).
    com_sale_ids = {
        r[0] for r in db.session.query(Sale.client_id).distinct().all()
    }
    fechadas = [
        {"seller_id": s.seller_id, "partner_id": s.partner_id,
         "value": float(s.total_value or 0)}
        for s in db.session.query(Sale).filter(
            Sale.sale_date >= start.date(),
            Sale.sale_date < end.date(),
        ).all()
    ]
    fechadas += [
        {"seller_id": c.seller_id, "partner_id": c.partner_id,
         "value": float(c.estimated_value or 0)}
        for c in db.session.query(Client).filter(
            Client.closed_at.isnot(None),
            Client.closed_at >= start,
            Client.closed_at < end,
        ).all()
        if c.id not in com_sale_ids
    ]

    regras = [r for r in db.session.query(CommissionRule).all() if _regra_vale(r, start, end)]

    linhas = []
    for r in regras:
        if r.seller_id:
            vendas = [v for v in fechadas if v["seller_id"] == r.seller_id]
            quem = r.seller.username if r.seller else "vendedor removido"
            tipo = "VENDEDOR"
        elif r.partner_id:
            vendas = [v for v in fechadas if v["partner_id"] == r.partner_id]
            quem = r.partner.name if r.partner else "parceiro removido"
            tipo = "PARCEIRO"
        else:
            continue  # regra sem dono nao calcula nada

        vendido = round(sum(v["value"] for v in vendas), 2)
        pct = float(r.percent or 0)
        linhas.append({
            "rule_id": r.id,
            "kind": tipo,
            "seller_id": r.seller_id,
            "partner_id": r.partner_id,
            "name": quem,
            "percent": pct,
            "sales_count": len(vendas),
            "sold_value": vendido,
            "commission_value": round(vendido * pct / 100.0, 2),
        })

    linhas.sort(key=lambda x: x["commission_value"], reverse=True)

    # Vendas fechadas que nao entram na conta de ninguem: mostrar em vez de sumir.
    com_vendedor = {r.seller_id for r in regras if r.seller_id}
    sem_vendedor = [v for v in fechadas if not v["seller_id"] or v["seller_id"] not in com_vendedor]
    sem_atribuicao = {
        "count": len(sem_vendedor),
        "sold_value": round(sum(v["value"] for v in sem_vendedor), 2),
    }

    return jsonify({
        "year": start.year,
        "month": start.month if end.month != 1 or start.month != 1 else None,
        "total_sold": round(sum(v["value"] for v in fechadas), 2),
        "closed_count": len(fechadas),
        "total_commission": round(sum(l["commission_value"] for l in linhas), 2),
        "rows": linhas,
        "sem_atribuicao": sem_atribuicao,
    })


# ── CRUD das regras ───────────────────────────────────────────────────
def _validar(data, partial=False):
    if not partial or "percent" in data:
        try:
            pct = float(data.get("percent"))
        except (TypeError, ValueError):
            return None, (jsonify({"detail": "percent invalido"}), 400)
        if pct < 0 or pct > 100:
            return None, (jsonify({"detail": "percent deve ficar entre 0 e 100"}), 400)
    return True, None


@bp.get("/api/commission-rules/options")
@token_required()
def rule_options():
    """Quem pode receber comissao: usuarios e parceiros, so id e nome.

    Endpoint proprio em vez de um /api/users generico: o seletor de regra so
    precisa de id e nome — nao ha razao para expor e-mail, papel ou qualquer
    outro campo de usuario aqui.
    """
    usuarios = db.session.query(User).order_by(User.username).all()
    parceiros = db.session.query(Partner).order_by(Partner.name).all()
    return jsonify({
        "sellers": [{"id": u.id, "name": u.name or u.username} for u in usuarios],
        "partners": [{"id": p.id, "name": p.name} for p in parceiros],
    })


@bp.get("/api/commission-rules")
@token_required()
def list_rules():
    regras = db.session.query(CommissionRule).order_by(CommissionRule.created_at.desc()).all()
    return jsonify([r.to_dict() for r in regras])


@bp.post("/api/commission-rules")
@token_required(roles=["ADMIN", "GERENTE"])
def create_rule():
    data = body_json()
    ok, erro = _validar(data)
    if erro:
        return erro

    seller_id = data.get("seller_id") or None
    partner_id = data.get("partner_id") or None
    if bool(seller_id) == bool(partner_id):
        return jsonify({"detail": "informe vendedor OU parceiro (exatamente um)"}), 400
    if seller_id and not db.session.get(User, seller_id):
        return jsonify({"detail": "Vendedor nao encontrado"}), 404
    if partner_id and not db.session.get(Partner, partner_id):
        return jsonify({"detail": "Parceiro nao encontrado"}), 404

    def _data(campo):
        if not data.get(campo):
            return None
        try:
            return parse_date(data.get(campo))
        except ValueError:
            return "invalida"

    vf, vu = _data("valid_from"), _data("valid_until")
    if vf == "invalida" or vu == "invalida":
        return jsonify({"detail": "vigencia invalida"}), 400

    r = CommissionRule(
        seller_id=seller_id, partner_id=partner_id,
        percent=float(data.get("percent")),
        valid_from=vf, valid_until=vu,
        active=bool(data.get("active", True)),
        notes=(data.get("notes") or "").strip(),
        created_at=utcnow(),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@bp.put("/api/commission-rules/<rule_id>")
@token_required(roles=["ADMIN", "GERENTE"])
def update_rule(rule_id):
    r = db.session.get(CommissionRule, rule_id)
    if not r:
        return jsonify({"detail": "Regra nao encontrada"}), 404
    data = body_json()
    ok, erro = _validar(data, partial=True)
    if erro:
        return erro

    if "percent" in data:
        r.percent = float(data.get("percent"))
    if "active" in data:
        r.active = bool(data.get("active"))
    if "notes" in data:
        r.notes = (data.get("notes") or "").strip()
    for campo in ("valid_from", "valid_until"):
        if campo in data:
            if not data.get(campo):
                setattr(r, campo, None)
            else:
                try:
                    setattr(r, campo, parse_date(data.get(campo)))
                except ValueError:
                    return jsonify({"detail": "vigencia invalida"}), 400

    db.session.commit()
    return jsonify(r.to_dict())


@bp.delete("/api/commission-rules/<rule_id>")
@token_required(roles=["ADMIN", "GERENTE"])
def delete_rule(rule_id):
    r = db.session.get(CommissionRule, rule_id)
    if not r:
        return jsonify({"detail": "Regra nao encontrada"}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({"ok": True})
