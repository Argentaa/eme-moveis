"""CRUD /api/projects (+ /overdue, /<id>/status) + checklists por etapa."""
from datetime import date, datetime, timezone

from flask import Blueprint, g, jsonify

from app.helpers import body_json, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import ChecklistItem, Funnel, Project, User, utcnow

bp = Blueprint("projects", __name__)

PROJECT_FIELDS = ("title", "client_id", "description", "status", "value", "deadline", "start_date", "planned_end_date", "actual_end_date", "steps", "funnel_id")


def _apply(data, project, partial=True):
    for f in PROJECT_FIELDS:
        if f == "funnel_id":
            continue
        if f in data:
            v = data[f]
            if f in ("deadline", "start_date", "planned_end_date", "actual_end_date"):
                v = parse_date(v)
            setattr(project, f, v)
    if "funnel_id" in data:
        raw = data.get("funnel_id")
        if raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
            funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
            project.funnel_id = funnel.id if funnel else None
        else:
            fid = str(raw).strip()
            funnel = db.session.get(Funnel, fid)
            if not funnel or funnel.kind != "PROJECTS" or not funnel.active:
                return "invalid"
            project.funnel_id = fid
    # actual_end_date de conclusao e gravado pelo endpoint /conclude, a partir
    # da flag explicita. NAO deduzir da chave da coluna: neste funil de
    # Producao a chave "CONCLUIDO" e a coluna "Medicao In Loco", entao olhar a
    # chave marcava como entregue um projeto que mal saiu da medicao.
    return None


def _resolve_funnel_for_create(data):
    raw = data.get("funnel_id") if "funnel_id" in data else None
    if "funnel_id" not in data or raw is None or (isinstance(raw, str) and str(raw).strip() == ""):
        funnel = db.session.query(Funnel).filter_by(kind="PROJECTS", is_default=True).first()
        return funnel.id if funnel else None
    fid = str(raw).strip()
    funnel = db.session.get(Funnel, fid)
    if not funnel or funnel.kind != "PROJECTS" or not funnel.active:
        return "invalid"
    return fid


@bp.get("/api/projects/overdue")
@token_required()
def overdue_projects():
    """Projetos com deadline vencido (qualquer status), com days_overdue.

    Contrato original: SELECT ..., DATEDIFF(CURDATE(), deadline) AS
    days_overdue WHERE deadline < CURDATE(). Frontend OverdueProjectsCard
    usa proj.days_overdue, proj.client_name, proj.deadline.
    """
    today = date.today()
    rows = (
        db.session.query(Project)
        .filter(Project.deadline.isnot(None), Project.deadline < today)
        .order_by(Project.deadline)
        .all()
    )
    out = []
    for p in rows:
        d = p.to_dict()
        try:
            d["days_overdue"] = (today - p.deadline).days if p.deadline else 0
        except Exception:
            d["days_overdue"] = 0
        out.append(d)
    return jsonify(out)


@bp.get("/api/projects/concluded")
@token_required()
def concluded_projects():
    """Projetos concluidos — alimenta a aba "Projetos entregues" do Pos-venda.

    Filtra pela flag explicita `concluded_at`, NAO pela coluna do funil: as
    colunas sao renomeadas pelo cliente e neste funil de Producao a chave
    "CONCLUIDO" esta numa coluna do meio ("Medicao In Loco").
    """
    rows = (
        db.session.query(Project)
        .filter(Project.concluded_at.isnot(None))
        .order_by(Project.concluded_at.desc())
        .all()
    )
    return jsonify([p.to_dict() for p in rows])


@bp.post("/api/projects/<project_id>/conclude")
@token_required()
def conclude_project(project_id):
    """Botao "Concluir projeto": sai da Producao e entra no Pos-venda.

    Idempotente: concluir duas vezes nao reescreve a data original.
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    if project.concluded_at is None:
        project.concluded_at = utcnow()
        if project.actual_end_date is None:
            project.actual_end_date = date.today()
    db.session.commit()
    return jsonify(project.to_dict())


@bp.post("/api/projects/<project_id>/reopen")
@token_required()
def reopen_project(project_id):
    """Desfaz a conclusao: o projeto volta para a Producao.

    Existe para o botao nao ser um beco sem saida — concluir por engano tem
    volta.
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    project.concluded_at = None
    db.session.commit()
    return jsonify(project.to_dict())


@bp.get("/api/projects")
@token_required()
def list_projects():
    rows = db.session.query(Project).order_by(Project.created_at.desc()).all()
    return jsonify([p.to_dict() for p in rows])


@bp.post("/api/projects")
@token_required()
def create_project():
    data = body_json()
    if not (data.get("title") or "").strip():
        return jsonify({"detail": "title e obrigatorio"}), 400
    if not data.get("client_id"):
        return jsonify({"detail": "client_id e obrigatorio"}), 400
    funnel_resolved = _resolve_funnel_for_create(data)
    if funnel_resolved == "invalid":
        return jsonify({"detail": "funnel_id invalido"}), 400
    status_val = data.get("status") or "ORCAMENTO"
    actual = parse_date(data.get("actual_end_date"))
    project = Project(
        title=data["title"].strip(),
        client_id=data["client_id"],
        description=data.get("description") or "",
        status=status_val,
        value=data.get("value") or 0,
        deadline=parse_date(data.get("deadline")),
        start_date=parse_date(data.get("start_date")),
        planned_end_date=parse_date(data.get("planned_end_date")),
        actual_end_date=actual,
        steps=data.get("steps") or [],
        funnel_id=funnel_resolved,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@bp.get("/api/projects/<project_id>")
@token_required()
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    return jsonify(project.to_dict())


@bp.put("/api/projects/<project_id>")
@token_required()
def update_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    data = body_json()
    res = _apply(data, project)
    if res == "invalid":
        return jsonify({"detail": "funnel_id invalido"}), 400
    db.session.commit()
    return jsonify(project.to_dict())


@bp.put("/api/projects/<project_id>/status")
@token_required()
def update_project_status(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    data = body_json()
    status = data.get("status")
    if not status:
        return jsonify({"detail": "status e obrigatorio"}), 400
    project.status = status
    if "steps" in data:
        project.steps = data["steps"]
    # permitir actual_end_date (e outras datas) também via rota de status
    if "actual_end_date" in data:
        project.actual_end_date = parse_date(data.get("actual_end_date"))
    if "start_date" in data:
        project.start_date = parse_date(data.get("start_date"))
    if "planned_end_date" in data:
        project.planned_end_date = parse_date(data.get("planned_end_date"))
    db.session.commit()
    return jsonify(project.to_dict())


@bp.put("/api/projects/<project_id>/steps")
@token_required()
def update_project_steps(project_id):
    """Atualiza apenas as etapas do projeto. Contrato original FastAPI.

    Frontend ProjectsView usa projectService.updateSteps -> PUT .../steps.
    """
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    steps = body_json().get("steps")
    if not isinstance(steps, list):
        return jsonify({"detail": "steps deve ser uma lista"}), 400
    project.steps = steps
    db.session.commit()
    return jsonify(project.to_dict())


@bp.delete("/api/projects/<project_id>")
@token_required()
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    db.session.delete(project)
    db.session.commit()
    return jsonify({"ok": True})


# ── CHECKLISTS POR ETAPA ─────────────────────────────────────────────

def _step_exists(project, step_id: str) -> bool:
    """Verifica se step_id existe no projeto.steps (lista de dicts com id)."""
    steps = getattr(project, "steps", None) or []
    if not isinstance(steps, list):
        return False
    sid = str(step_id).strip()
    for s in steps:
        if not isinstance(s, dict):
            continue
        val = s.get("id")
        if val is not None and str(val).strip() == sid:
            return True
    return False


@bp.get("/api/projects/<project_id>/checklists")
@token_required()
def list_checklists(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    rows = (
        db.session.query(ChecklistItem)
        .filter_by(project_id=project_id)
        .order_by(ChecklistItem.position)
        .all()
    )
    return jsonify([c.to_dict() for c in rows])


@bp.post("/api/projects/<project_id>/checklists")
@token_required()
def create_checklist(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    data = body_json()
    raw_step = data.get("step_id")
    if raw_step is None or (isinstance(raw_step, str) and not raw_step.strip()):
        return jsonify({"detail": "step_id e obrigatorio"}), 400
    step_id = str(raw_step).strip()
    if not _step_exists(project, step_id):
        return jsonify({"detail": "step_id invalido"}), 400
    raw_label = data.get("label")
    if raw_label is None or (isinstance(raw_label, str) and not raw_label.strip()):
        return jsonify({"detail": "label e obrigatorio"}), 400
    label = str(raw_label).strip()
    notes = data.get("notes")
    if notes is None:
        notes = ""
    else:
        notes = str(notes)
    # assigned_user_id opcional
    assigned_user_id = data.get("assigned_user_id")
    if assigned_user_id not in (None, ""):
        assigned_user_id = str(assigned_user_id).strip()
        if not assigned_user_id:
            assigned_user_id = None
        else:
            u = db.session.get(User, assigned_user_id)
            if not u:
                return jsonify({"detail": "Usuario nao encontrado"}), 404
    else:
        assigned_user_id = None
    completed_raw = data.get("completed")
    completed = bool(completed_raw) if completed_raw is not None else False
    completed_at = None
    if completed:
        completed_at = datetime.now(timezone.utc)
        # se marcado como concluido sem responsavel, atribuir ao usuario atual
        if not assigned_user_id and hasattr(g, "current_user") and getattr(g.current_user, "id", None):
            assigned_user_id = g.current_user.id
    # position auto incremento
    try:
        from sqlalchemy import func as _func  # pylint: disable=import-outside-toplevel
        max_pos = db.session.query(_func.coalesce(_func.max(ChecklistItem.position), -1)).filter(ChecklistItem.project_id == project_id).scalar()
        if max_pos is None:
            max_pos = -1
        position = int(max_pos) + 1
    except Exception:
        position = 0
    item = ChecklistItem(
        project_id=project_id,
        step_id=step_id,
        label=label,
        completed=completed,
        assigned_user_id=assigned_user_id,
        completed_at=completed_at,
        notes=notes or "",
        position=position,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.put("/api/checklist-items/<item_id>")
@token_required()
def update_checklist(item_id):
    item = db.session.get(ChecklistItem, item_id)
    if not item:
        return jsonify({"detail": "Checklist nao encontrada"}), 404
    data = body_json()
    # label
    if "label" in data:
        raw = data.get("label")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return jsonify({"detail": "label e obrigatorio"}), 400
        item.label = str(raw).strip()
    # step_id
    if "step_id" in data:
        raw_step = data.get("step_id")
        if raw_step is None or (isinstance(raw_step, str) and not raw_step.strip()):
            return jsonify({"detail": "step_id e obrigatorio"}), 400
        sid = str(raw_step).strip()
        proj = db.session.get(Project, item.project_id)
        if proj and not _step_exists(proj, sid):
            return jsonify({"detail": "step_id invalido"}), 400
        item.step_id = sid
    # notes
    if "notes" in data:
        raw_notes = data.get("notes")
        item.notes = str(raw_notes) if raw_notes is not None else ""
    # assigned_user_id
    if "assigned_user_id" in data:
        raw_uid = data.get("assigned_user_id")
        if raw_uid in (None, ""):
            item.assigned_user_id = None
        else:
            uid = str(raw_uid).strip()
            if not uid:
                item.assigned_user_id = None
            else:
                u = db.session.get(User, uid)
                if not u:
                    return jsonify({"detail": "Usuario nao encontrado"}), 404
                item.assigned_user_id = uid
    # completed bool
    if "completed" in data:
        new_completed = bool(data.get("completed"))
        old_completed = bool(item.completed)
        if new_completed and not old_completed:
            item.completed = True
            item.completed_at = datetime.now(timezone.utc)
            if not item.assigned_user_id and hasattr(g, "current_user") and getattr(g.current_user, "id", None):
                item.assigned_user_id = g.current_user.id
        elif not new_completed and old_completed:
            item.completed = False
            item.completed_at = None
        else:
            item.completed = new_completed
            if new_completed and item.completed_at is None:
                item.completed_at = datetime.now(timezone.utc)
            if not new_completed:
                item.completed_at = None
    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/api/checklist-items/<item_id>")
@token_required()
def delete_checklist(item_id):
    item = db.session.get(ChecklistItem, item_id)
    if not item:
        return jsonify({"detail": "Checklist nao encontrada"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})
