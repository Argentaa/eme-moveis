"""CRUD /api/projects (+ /overdue, /<id>/status)."""
from datetime import date

from flask import Blueprint, jsonify

from app.helpers import body_json, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import Project

bp = Blueprint("projects", __name__)

PROJECT_FIELDS = ("title", "client_id", "description", "status", "value", "deadline", "steps")


def _apply(data, project, partial=True):
    for f in PROJECT_FIELDS:
        if f in data:
            v = data[f]
            if f == "deadline":
                v = parse_date(v)
            setattr(project, f, v)


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
    project = Project(
        title=data["title"].strip(),
        client_id=data["client_id"],
        description=data.get("description") or "",
        status=data.get("status") or "ORCAMENTO",
        value=data.get("value") or 0,
        deadline=parse_date(data.get("deadline")),
        steps=data.get("steps") or [],
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
    _apply(body_json(), project)
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
