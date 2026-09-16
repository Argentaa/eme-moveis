"""CRUD /api/projects (+ /overdue, /<id>/status)."""
from datetime import date

from flask import Blueprint, jsonify

from app.helpers import body_json, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import Funnel, Project

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
    # auto-preenche actual_end_date ao concluir
    if getattr(project, "status", None) == "CONCLUIDO" and getattr(project, "actual_end_date", None) is None:
        project.actual_end_date = date.today()
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
    if status_val == "CONCLUIDO" and actual is None:
        actual = date.today()
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
    if project.status == "CONCLUIDO" and project.actual_end_date is None:
        project.actual_end_date = date.today()
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
