"""Agenda e check-ins de pos-venda (Fase 8: 8.5 + 8.6).

Duas pecas:

- **Follow-ups programados (8.5):** `CalendarEvent` tipo `POS_VENDA` criados N
  dias apos `Project.actual_end_date`. Os dias vêm de `app_settings`
  (`posvenda_followup_days`, ex. "7,30"; default 7 e 30). A geracao e
  idempotente por (project_id, type, start_date) e nunca cria evento no
  passado — projeto entregue ha 60 dias nao ganha retrospecto de 7 dias.
  O botao "Concluir projeto" ja agenda sozinho; o endpoint de geracao serve
  para projetos concluidos antes da Fase 8 e para reagendar apos mudar os dias.
- **Check-ins (8.6):** `Interaction` tipo LIGACAO/VISITA/WHATSAPP com o
  marcador `[CHECK-IN PÓS-VENDA]` no inicio do conteudo. O marcador e o que
  separa check-in de contato comum no historico — a aba lista feitos de um
  lado e programados (eventos POS_VENDA) do outro.
"""
from datetime import date, timedelta

from flask import Blueprint, g, jsonify

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import AppSetting, CalendarEvent, Client, Interaction, Project, utcnow

bp = Blueprint("posvenda", __name__)

CHECKIN_MARK = "[CHECK-IN PÓS-VENDA]"
CHECKIN_TYPES = ("LIGACAO", "VISITA", "WHATSAPP")
DEFAULT_FOLLOWUP_DAYS = (7, 30)


def _followup_days():
    """Dias de contato lidos do app_settings; default 7 e 30."""
    row = db.session.query(AppSetting).filter_by(key="posvenda_followup_days").first()
    raw = (row.value or "") if row else ""
    dias = []
    for parte in raw.replace(";", ",").split(","):
        parte = parte.strip()
        if parte.isdigit() and 0 < int(parte) <= 365:
            dias.append(int(parte))
    return sorted(set(dias)) or list(DEFAULT_FOLLOWUP_DAYS)


def _ensure_followups(project):
    """Cria os POS_VENDA do projeto que ainda nao existem. Retorna os criados.

    Nao faz commit — quem chama decide (o conclude commita junto; o endpoint
    de geracao commita no fim do lote).
    """
    if project.actual_end_date is None:
        return []
    hoje = date.today()
    criados = []
    for dias in _followup_days():
        alvo = project.actual_end_date + timedelta(days=dias)
        if alvo < hoje:
            continue
        existe = (
            db.session.query(CalendarEvent)
            .filter_by(project_id=project.id, type="POS_VENDA", start_date=alvo)
            .first()
        )
        if existe:
            continue
        ev = CalendarEvent(
            title=f"Pós-venda {dias} dias — {project.title}",
            description=f"Contato programado de pós-venda ({dias} dias após a entrega em {project.actual_end_date.isoformat()}).",
            type="POS_VENDA",
            status="AGENDADO",
            start_date=alvo,
            project_id=project.id,
            client_id=project.client_id,
        )
        db.session.add(ev)
        criados.append(ev)
    return criados


# ── check-ins ─────────────────────────────────────────────────────────


@bp.get("/api/posvenda/checkins")
@token_required()
def list_checkins():
    """Check-ins feitos (interacoes com o marcador), mais novos primeiro."""
    rows = (
        db.session.query(Interaction)
        .filter(Interaction.content.like(f"{CHECKIN_MARK}%"))
        .order_by(Interaction.created_at.desc())
        .all()
    )
    out = []
    for r in rows:
        d = r.to_dict()
        d["client_name"] = r.client.name if r.client else None
        out.append(d)
    return jsonify(out)


@bp.post("/api/posvenda/checkins")
@token_required()
def create_checkin():
    """Registra um check-in de pos-venda no historico do cliente."""
    data = body_json()
    client_id = data.get("client_id")
    if not client_id or not db.session.get(Client, client_id):
        return jsonify({"detail": "Cliente nao encontrado"}), 404
    itype = (data.get("type") or "").upper()
    if itype not in CHECKIN_TYPES:
        return jsonify({"detail": "type deve ser LIGACAO, VISITA ou WHATSAPP"}), 400
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"detail": "content e obrigatorio"}), 400
    project_id = data.get("project_id") or None
    if project_id:
        project = db.session.get(Project, project_id)
        if not project:
            return jsonify({"detail": "Projeto nao encontrado"}), 404
        content = f"{content} (projeto: {project.title})"
    row = Interaction(
        client_id=client_id,
        type=itype,
        content=f"{CHECKIN_MARK} {content}",
        created_by=g.current_user.username if hasattr(g, "current_user") else "",
        automatic=False,
    )
    db.session.add(row)
    db.session.commit()
    d = row.to_dict()
    d["client_name"] = row.client.name if row.client else None
    return jsonify(d), 201


# ── follow-ups programados ────────────────────────────────────────────


@bp.post("/api/posvenda/followups/generate")
@token_required()
def generate_followups():
    """Gera os contatos programados. Com `project_id`, so aquele projeto;
    sem, todos os concluidos. Idempotente: reexecutar nao duplica."""
    data = body_json()
    project_id = data.get("project_id") or None
    if project_id:
        project = db.session.get(Project, project_id)
        if not project:
            return jsonify({"detail": "Projeto nao encontrado"}), 404
        if project.concluded_at is None:
            return jsonify({"detail": "Projeto ainda nao concluido"}), 409
        projetos = [project]
    else:
        projetos = (
            db.session.query(Project).filter(Project.concluded_at.isnot(None)).all()
        )
    criados = 0
    for p in projetos:
        criados += len(_ensure_followups(p))
    db.session.commit()
    return jsonify({"created": criados, "projects": len(projetos),
                    "days": _followup_days()})
