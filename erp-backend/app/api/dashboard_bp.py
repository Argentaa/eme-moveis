"""Bloco "O que precisa da minha atencao" do painel inicial.

Agrega pendencias que ja existem em outros modulos (financeiro, pos-venda,
producao e comercial) numa lista unica, com o modulo/aba de destino para a UI
levar o usuario direto ao ponto. Nada aqui cria dado — e so leitura.
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from app.auth import token_required
from app.extensions import db
from app.helpers import iso
from app.models.models import Client, FinancialRecord, Interaction, Project, ServiceTicket, utcnow

bp = Blueprint("dashboard", __name__)

WARN_DAYS = 7          # contas a vencer nos proximos N dias
NO_REPLY_DAYS = 7      # orcamento sem retorno ha mais de N dias
OPEN_TICKET_STATUS = ("ABERTO", "EM_ANALISE")


def _fmt_brl(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pending(status="PENDENTE"):
    return db.session.query(FinancialRecord).filter(FinancialRecord.status == status)


@bp.get("/api/dashboard/attention")
@token_required()
def attention():
    today = date.today()
    items = []

    # ── Contas vencidas
    overdue = _pending().filter(
        FinancialRecord.due_date.isnot(None),
        FinancialRecord.due_date < today,
    ).all()
    if overdue:
        total = sum(float(r.amount or 0) for r in overdue)
        items.append({
            "kind": "CONTA_VENCIDA",
            "label": f"{len(overdue)} conta(s) vencida(s)",
            "detail": "Lancamentos em aberto com vencimento passado",
            "count": len(overdue),
            "total": _fmt_brl(total),
            "tone": "negative",
            "module": "financial",
            "tab": "overdue",
        })

    # ── Contas a vencer nos proximos dias
    limit = today + timedelta(days=WARN_DAYS)
    upcoming = _pending().filter(
        FinancialRecord.due_date.isnot(None),
        FinancialRecord.due_date >= today,
        FinancialRecord.due_date <= limit,
    ).all()
    if upcoming:
        total = sum(float(r.amount or 0) for r in upcoming)
        items.append({
            "kind": "CONTA_A_VENCER",
            "label": f"{len(upcoming)} conta(s) vencendo em {WARN_DAYS} dias",
            "detail": "Lancamentos em aberto com vencimento proximo",
            "count": len(upcoming),
            "total": _fmt_brl(total),
            "tone": "warning",
            "module": "financial",
            "tab": "overdue",
        })

    # ── Chamados de pos-venda em aberto
    tickets = db.session.query(ServiceTicket).filter(
        ServiceTicket.status.in_(OPEN_TICKET_STATUS)).all()
    if tickets:
        items.append({
            "kind": "CHAMADO_ABERTO",
            "label": f"{len(tickets)} chamado(s) em aberto",
            "detail": "Solicitacoes de pos-venda sem resolucao",
            "count": len(tickets),
            "total": None,
            "tone": "warning",
            "module": "tickets",
            "tab": "tickets",
        })

    # ── Projetos atrasados (deadline vencido e nao concluido)
    late = [p for p in db.session.query(Project).all()
            if p.status != "CONCLUIDO" and p.deadline and p.deadline < today]
    if late:
        items.append({
            "kind": "PROJETO_ATRASADO",
            "label": f"{len(late)} projeto(s) atrasado(s)",
            "detail": "Prazo de entrega vencido",
            "count": len(late),
            "total": None,
            "tone": "negative",
            "module": "production",
            "tab": "kanban",
        })

    # ── Orcamentos/propostas sem retorno
    cutoff = date.today() - timedelta(days=NO_REPLY_DAYS)
    stalled = []
    candidates = db.session.query(Client).filter(
        db.or_(
            Client.funnel_status.ilike("%ORCAMENTO%"),
            Client.funnel_status.ilike("%PROPOSTA%"),
        )
    ).all()
    for c in candidates:
        last = (db.session.query(Interaction)
                .filter(Interaction.client_id == c.id)
                .order_by(Interaction.created_at.desc())
                .first())
        if last is None or (last.created_at and last.created_at.date() < cutoff):
            stalled.append(c)
    if stalled:
        items.append({
            "kind": "ORCAMENTO_SEM_RETORNO",
            "label": f"{len(stalled)} orcamento(s) sem retorno",
            "detail": f"Sem interacao ha mais de {NO_REPLY_DAYS} dias",
            "count": len(stalled),
            "total": None,
            "tone": "warning",
            "module": "commercial",
            "tab": "funnel",
        })

    return jsonify({
        "generated_at": iso(utcnow()),
        "reference_date": today.isoformat(),
        "total_items": sum(i["count"] for i in items),
        "items": items,
    })
