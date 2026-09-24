"""Blueprint production - ambientes, funcionarios, maquinas, apontamentos e ocorrencias."""
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request, g

from app.extensions import db
from app.helpers import body_json, iso, num, parse_date
from app.auth import token_required
from app.models.models import (
    Project, ProjectEnvironment, Worker, Machine, TimeEntry, ProductionIssue, ChecklistItem,
)

bp = Blueprint("production", __name__)

ENV_TYPES = {"COZINHA", "QUARTO", "SALA", "PAINEL", "ESCRITORIO", "OUTRO"}
ISSUE_KINDS = {"RETRABALHO", "DESPERDICIO", "PERDA"}
HOURS_TYPES = {"PRODUTIVA", "IMPRODUTIVA"}
ENV_STATUSES = {"PLANEJADO", "EM_PRODUCAO", "CONCLUIDO"}


def _creator():
    return g.current_user.username if hasattr(g, "current_user") else ""


def _num_ge0(raw, field_name):
    """Convert raw to float via num; returns (value, error_detail)."""
    if raw is None or raw == "":
        return None, None
    v = num(raw)
    # num returns original if not convertible -> treat as invalid
    if v is None:
        return None, f"{field_name} invalido"
    # if v still string (not numeric)
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return None, f"{field_name} invalido"
    import math
    if math.isnan(fv) or math.isinf(fv):
        return None, f"{field_name} invalido"
    if fv < 0:
        return None, f"{field_name} deve ser maior ou igual a zero"
    return fv, None


# ── WORKERS ───────────────────────────────────────────────────────────

@bp.get("/api/workers")
@token_required()
def list_workers():
    rows = db.session.query(Worker).order_by(Worker.name).all()
    return jsonify([w.to_dict() for w in rows])


@bp.post("/api/workers")
@token_required()
def create_worker():
    data = body_json()
    name = (data.get("name") or "").strip() if isinstance(data.get("name"), str) else ""
    # also handle non-string?
    if isinstance(data.get("name"), str):
        name = data.get("name", "").strip()
    else:
        name = str(data.get("name", "")).strip() if data.get("name") is not None else ""
    if not name:
        return jsonify({"detail": "name e obrigatorio"}), 400
    exists = db.session.query(Worker).filter(Worker.name == name).first()
    if exists:
        return jsonify({"detail": "Funcionario ja existe"}), 400
    w = Worker(name=name, active=True)
    db.session.add(w)
    db.session.commit()
    return jsonify(w.to_dict()), 201


@bp.put("/api/workers/<worker_id>")
@token_required()
def update_worker(worker_id):
    w = db.session.get(Worker, worker_id)
    if not w:
        return jsonify({"detail": "Funcionario nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        raw = data.get("name")
        if not isinstance(raw, str) or not raw.strip():
            return jsonify({"detail": "name e obrigatorio"}), 400
        name = raw.strip()
        # unique check excluding self
        exists = db.session.query(Worker).filter(Worker.name == name, Worker.id != worker_id).first()
        if exists:
            return jsonify({"detail": "Funcionario ja existe"}), 400
        w.name = name
    if "active" in data:
        v = data.get("active")
        if not isinstance(v, bool):
            return jsonify({"detail": "active deve ser booleano"}), 400
        w.active = v
    db.session.commit()
    return jsonify(w.to_dict())


@bp.delete("/api/workers/<worker_id>")
@token_required()
def delete_worker(worker_id):
    w = db.session.get(Worker, worker_id)
    if not w:
        return jsonify({"detail": "Funcionario nao encontrado"}), 404
    # check uso em TimeEntry ou ProductionIssue
    has_time = db.session.query(TimeEntry).filter_by(worker_id=worker_id).first() is not None
    has_issue = db.session.query(ProductionIssue).filter_by(worker_id=worker_id).first() is not None
    if has_time or has_issue:
        return jsonify({"detail": "Funcionario em uso"}), 400
    db.session.delete(w)
    db.session.commit()
    return jsonify({"ok": True})


# ── MACHINES ──────────────────────────────────────────────────────────

@bp.get("/api/machines")
@token_required()
def list_machines():
    rows = db.session.query(Machine).order_by(Machine.name).all()
    return jsonify([m.to_dict() for m in rows])


@bp.post("/api/machines")
@token_required()
def create_machine():
    data = body_json()
    raw = data.get("name")
    if not isinstance(raw, str) or not raw.strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    name = raw.strip()
    exists = db.session.query(Machine).filter(Machine.name == name).first()
    if exists:
        return jsonify({"detail": "Maquina ja existe"}), 400
    m = Machine(name=name, active=True)
    db.session.add(m)
    db.session.commit()
    return jsonify(m.to_dict()), 201


@bp.put("/api/machines/<machine_id>")
@token_required()
def update_machine(machine_id):
    m = db.session.get(Machine, machine_id)
    if not m:
        return jsonify({"detail": "Maquina nao encontrada"}), 404
    data = body_json()
    if "name" in data:
        raw = data.get("name")
        if not isinstance(raw, str) or not raw.strip():
            return jsonify({"detail": "name e obrigatorio"}), 400
        name = raw.strip()
        exists = db.session.query(Machine).filter(Machine.name == name, Machine.id != machine_id).first()
        if exists:
            return jsonify({"detail": "Maquina ja existe"}), 400
        m.name = name
    if "active" in data:
        v = data.get("active")
        if not isinstance(v, bool):
            return jsonify({"detail": "active deve ser booleano"}), 400
        m.active = v
    db.session.commit()
    return jsonify(m.to_dict())


@bp.delete("/api/machines/<machine_id>")
@token_required()
def delete_machine(machine_id):
    m = db.session.get(Machine, machine_id)
    if not m:
        return jsonify({"detail": "Maquina nao encontrada"}), 404
    has_time = db.session.query(TimeEntry).filter_by(machine_id=machine_id).first() is not None
    if has_time:
        return jsonify({"detail": "Maquina em uso"}), 400
    db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True})


# ── ENVIRONMENTS ──────────────────────────────────────────────────────

@bp.get("/api/projects/<project_id>/environments")
@token_required()
def list_environments(project_id):
    proj = db.session.get(Project, project_id)
    if not proj:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    rows = db.session.query(ProjectEnvironment).filter_by(project_id=project_id).order_by(ProjectEnvironment.created_at).all()
    return jsonify([e.to_dict() for e in rows])


@bp.post("/api/projects/<project_id>/environments")
@token_required()
def create_environment(project_id):
    proj = db.session.get(Project, project_id)
    if not proj:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    data = body_json()
    raw_name = data.get("name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return jsonify({"detail": "name e obrigatorio"}), 400
    name = raw_name.strip()

    env_type = data.get("env_type")
    if env_type is not None and env_type != "":
        if not isinstance(env_type, str):
            return jsonify({"detail": "env_type invalido"}), 400
        env_type = env_type.strip().upper()
        if env_type not in ENV_TYPES:
            return jsonify({"detail": "env_type invalido"}), 400
    else:
        env_type = "OUTRO"

    status = data.get("status")
    if status is not None and status != "":
        if not isinstance(status, str):
            return jsonify({"detail": "status invalido"}), 400
        status = status.strip().upper()
        if status not in ENV_STATUSES:
            return jsonify({"detail": "status invalido"}), 400
    else:
        status = "PLANEJADO"

    # area_m2
    area_m2 = None
    if "area_m2" in data and data.get("area_m2") not in (None, ""):
        fv, err = _num_ge0(data.get("area_m2"), "area_m2")
        if err:
            return jsonify({"detail": err}), 400
        area_m2 = fv

    # value
    value = None
    if "value" in data and data.get("value") not in (None, ""):
        fv, err = _num_ge0(data.get("value"), "value")
        if err:
            return jsonify({"detail": err}), 400
        value = fv

    env = ProjectEnvironment(
        project_id=project_id,
        name=name,
        env_type=env_type,
        area_m2=area_m2,
        value=value,
        status=status,
    )
    db.session.add(env)
    db.session.commit()
    return jsonify(env.to_dict()), 201


@bp.put("/api/environments/<env_id>")
@token_required()
def update_environment(env_id):
    env = db.session.get(ProjectEnvironment, env_id)
    if not env:
        return jsonify({"detail": "Ambiente nao encontrado"}), 404
    data = body_json()
    if "name" in data:
        raw = data.get("name")
        if not isinstance(raw, str) or not raw.strip():
            return jsonify({"detail": "name e obrigatorio"}), 400
        env.name = raw.strip()
    if "env_type" in data:
        raw = data.get("env_type")
        if raw is not None and raw != "":
            if not isinstance(raw, str):
                return jsonify({"detail": "env_type invalido"}), 400
            v = raw.strip().upper()
            if v not in ENV_TYPES:
                return jsonify({"detail": "env_type invalido"}), 400
            env.env_type = v
    if "status" in data:
        raw = data.get("status")
        if raw is not None and raw != "":
            if not isinstance(raw, str):
                return jsonify({"detail": "status invalido"}), 400
            v = raw.strip().upper()
            if v not in ENV_STATUSES:
                return jsonify({"detail": "status invalido"}), 400
            env.status = v
    if "area_m2" in data:
        raw = data.get("area_m2")
        if raw in (None, ""):
            env.area_m2 = None
        else:
            fv, err = _num_ge0(raw, "area_m2")
            if err:
                return jsonify({"detail": err}), 400
            env.area_m2 = fv
    if "value" in data:
        raw = data.get("value")
        if raw in (None, ""):
            env.value = None
        else:
            fv, err = _num_ge0(raw, "value")
            if err:
                return jsonify({"detail": err}), 400
            env.value = fv
    db.session.commit()
    return jsonify(env.to_dict())


@bp.delete("/api/environments/<env_id>")
@token_required()
def delete_environment(env_id):
    env = db.session.get(ProjectEnvironment, env_id)
    if not env:
        return jsonify({"detail": "Ambiente nao encontrado"}), 404
    # FK SET NULL - just delete; any TimeEntry referencing will have environment_id set null
    # ensure ORM nulls? DB will SET NULL on commit but for safety set explicitly if needed via query
    # We'll null out before delete to handle sqlite without FK enforcement
    db.session.query(TimeEntry).filter_by(environment_id=env_id).update({"environment_id": None})
    db.session.delete(env)
    db.session.commit()
    return jsonify({"ok": True})


# ── TIME ENTRIES ──────────────────────────────────────────────────────

@bp.get("/api/projects/<project_id>/time")
@token_required()
def list_time_entries(project_id):
    proj = db.session.get(Project, project_id)
    if not proj:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    rows = db.session.query(TimeEntry).filter_by(project_id=project_id).order_by(TimeEntry.work_date.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/projects/<project_id>/time")
@token_required()
def create_time_entry(project_id):
    proj = db.session.get(Project, project_id)
    if not proj:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    data = body_json()

    # hours obrigatorio
    if "hours" not in data or data.get("hours") in (None, ""):
        return jsonify({"detail": "hours e obrigatorio"}), 400
    # validate hours >0
    try:
        hv = float(data.get("hours"))
    except (TypeError, ValueError):
        return jsonify({"detail": "hours invalido"}), 400
    import math
    if math.isnan(hv) or math.isinf(hv):
        return jsonify({"detail": "hours invalido"}), 400
    if hv <= 0:
        return jsonify({"detail": "hours deve ser maior que zero"}), 400

    # work_date obrigatorio
    raw_date = data.get("work_date")
    if raw_date in (None, ""):
        return jsonify({"detail": "work_date e obrigatorio"}), 400
    try:
        wd = parse_date(raw_date)
    except Exception:
        return jsonify({"detail": "work_date invalida"}), 400
    if wd is None:
        return jsonify({"detail": "work_date invalida"}), 400

    # hours_type
    hours_type = data.get("hours_type")
    if hours_type not in (None, ""):
        if not isinstance(hours_type, str):
            return jsonify({"detail": "hours_type invalido"}), 400
        hours_type = hours_type.strip().upper()
        if hours_type not in HOURS_TYPES:
            return jsonify({"detail": "hours_type invalido"}), 400
    else:
        hours_type = "PRODUTIVA"

    # environment_id
    env_id = data.get("environment_id")
    if env_id not in (None, ""):
        env = db.session.get(ProjectEnvironment, env_id)
        if not env:
            return jsonify({"detail": "Ambiente nao encontrado"}), 404
        if str(env.project_id) != str(project_id):
            return jsonify({"detail": "Ambiente nao pertence ao projeto"}), 404
    else:
        env_id = None

    # worker_id
    worker_id = data.get("worker_id")
    if worker_id not in (None, ""):
        w = db.session.get(Worker, worker_id)
        if not w:
            return jsonify({"detail": "Funcionario nao encontrado"}), 404
    else:
        worker_id = None

    # machine_id
    machine_id = data.get("machine_id")
    if machine_id not in (None, ""):
        m = db.session.get(Machine, machine_id)
        if not m:
            return jsonify({"detail": "Maquina nao encontrada"}), 404
    else:
        machine_id = None

    notes = data.get("notes") or ""

    te = TimeEntry(
        project_id=project_id,
        environment_id=env_id,
        worker_id=worker_id,
        machine_id=machine_id,
        hours=hv,
        hours_type=hours_type,
        work_date=wd,
        notes=notes,
        created_by=_creator(),
    )
    db.session.add(te)
    db.session.commit()
    return jsonify(te.to_dict()), 201


@bp.put("/api/time-entries/<entry_id>")
@token_required()
def update_time_entry(entry_id):
    te = db.session.get(TimeEntry, entry_id)
    if not te:
        return jsonify({"detail": "Apontamento nao encontrado"}), 404
    data = body_json()

    if "hours" in data:
        raw = data.get("hours")
        if raw in (None, ""):
            return jsonify({"detail": "hours invalido"}), 400
        try:
            hv = float(raw)
        except (TypeError, ValueError):
            return jsonify({"detail": "hours invalido"}), 400
        import math
        if math.isnan(hv) or math.isinf(hv):
            return jsonify({"detail": "hours invalido"}), 400
        if hv <= 0:
            return jsonify({"detail": "hours deve ser maior que zero"}), 400
        te.hours = hv

    if "hours_type" in data:
        raw = data.get("hours_type")
        if raw not in (None, ""):
            if not isinstance(raw, str):
                return jsonify({"detail": "hours_type invalido"}), 400
            v = raw.strip().upper()
            if v not in HOURS_TYPES:
                return jsonify({"detail": "hours_type invalido"}), 400
            te.hours_type = v

    if "work_date" in data:
        raw = data.get("work_date")
        if raw in (None, ""):
            return jsonify({"detail": "work_date invalida"}), 400
        try:
            wd = parse_date(raw)
        except Exception:
            return jsonify({"detail": "work_date invalida"}), 400
        if wd is None:
            return jsonify({"detail": "work_date invalida"}), 400
        te.work_date = wd

    if "environment_id" in data:
        raw = data.get("environment_id")
        if raw in (None, ""):
            te.environment_id = None
        else:
            env = db.session.get(ProjectEnvironment, raw)
            if not env:
                return jsonify({"detail": "Ambiente nao encontrado"}), 404
            # ensure same project
            if str(env.project_id) != str(te.project_id):
                return jsonify({"detail": "Ambiente nao pertence ao projeto"}), 404
            te.environment_id = raw

    if "worker_id" in data:
        raw = data.get("worker_id")
        if raw in (None, ""):
            te.worker_id = None
        else:
            w = db.session.get(Worker, raw)
            if not w:
                return jsonify({"detail": "Funcionario nao encontrado"}), 404
            te.worker_id = raw

    if "machine_id" in data:
        raw = data.get("machine_id")
        if raw in (None, ""):
            te.machine_id = None
        else:
            m = db.session.get(Machine, raw)
            if not m:
                return jsonify({"detail": "Maquina nao encontrada"}), 404
            te.machine_id = raw

    if "notes" in data:
        te.notes = data.get("notes") or ""

    db.session.commit()
    return jsonify(te.to_dict())


@bp.delete("/api/time-entries/<entry_id>")
@token_required()
def delete_time_entry(entry_id):
    te = db.session.get(TimeEntry, entry_id)
    if not te:
        return jsonify({"detail": "Apontamento nao encontrado"}), 404
    db.session.delete(te)
    db.session.commit()
    return jsonify({"ok": True})


# ── ISSUES ────────────────────────────────────────────────────────────

@bp.get("/api/projects/<project_id>/issues")
@token_required()
def list_issues(project_id):
    proj = db.session.get(Project, project_id)
    if not proj:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    rows = db.session.query(ProductionIssue).filter_by(project_id=project_id).order_by(ProductionIssue.created_at.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@bp.post("/api/projects/<project_id>/issues")
@token_required()
def create_issue(project_id):
    proj = db.session.get(Project, project_id)
    if not proj:
        return jsonify({"detail": "Projeto nao encontrado"}), 404
    data = body_json()

    kind = data.get("kind")
    if kind is None or (isinstance(kind, str) and not kind.strip()):
        return jsonify({"detail": "kind e obrigatorio"}), 400
    if not isinstance(kind, str):
        return jsonify({"detail": "kind invalido"}), 400
    kind = kind.strip().upper()
    if kind not in ISSUE_KINDS:
        return jsonify({"detail": "kind invalido"}), 400

    # worker_id validate if provided
    worker_id = data.get("worker_id")
    if worker_id not in (None, ""):
        w = db.session.get(Worker, worker_id)
        if not w:
            return jsonify({"detail": "Funcionario nao encontrado"}), 404
    else:
        worker_id = None

    material = data.get("material")
    if material is not None and not isinstance(material, str):
        material = str(material)
    if isinstance(material, str):
        material = material.strip()
        if material == "":
            material = ""
    else:
        material = ""

    # quantity
    quantity = None
    if "quantity" in data and data.get("quantity") not in (None, ""):
        fv, err = _num_ge0(data.get("quantity"), "quantity")
        if err:
            return jsonify({"detail": err}), 400
        quantity = fv

    # hours_spent
    hours_spent = None
    if "hours_spent" in data and data.get("hours_spent") not in (None, ""):
        fv, err = _num_ge0(data.get("hours_spent"), "hours_spent")
        if err:
            return jsonify({"detail": err}), 400
        hours_spent = fv

    # cost
    cost = None
    if "cost" in data and data.get("cost") not in (None, ""):
        fv, err = _num_ge0(data.get("cost"), "cost")
        if err:
            return jsonify({"detail": err}), 400
        cost = fv

    # issue_date: if absent uses today
    raw_date = data.get("issue_date")
    if raw_date in (None, ""):
        issue_date = date.today()
    else:
        try:
            issue_date = parse_date(raw_date)
        except Exception:
            return jsonify({"detail": "issue_date invalida"}), 400
        if issue_date is None:
            return jsonify({"detail": "issue_date invalida"}), 400

    reason = data.get("reason") or ""
    if isinstance(reason, str):
        reason = reason.strip()
    notes = data.get("notes") or ""

    iss = ProductionIssue(
        project_id=project_id,
        kind=kind,
        worker_id=worker_id,
        material=material or "",
        quantity=quantity,
        hours_spent=hours_spent,
        cost=cost,
        reason=reason,
        issue_date=issue_date,
        notes=notes,
    )
    db.session.add(iss)
    db.session.commit()
    return jsonify(iss.to_dict()), 201


@bp.put("/api/issues/<issue_id>")
@token_required()
def update_issue(issue_id):
    iss = db.session.get(ProductionIssue, issue_id)
    if not iss:
        return jsonify({"detail": "Ocorrencia nao encontrada"}), 404
    data = body_json()

    if "kind" in data:
        raw = data.get("kind")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return jsonify({"detail": "kind invalido"}), 400
        if not isinstance(raw, str):
            return jsonify({"detail": "kind invalido"}), 400
        v = raw.strip().upper()
        if v not in ISSUE_KINDS:
            return jsonify({"detail": "kind invalido"}), 400
        iss.kind = v

    if "worker_id" in data:
        raw = data.get("worker_id")
        if raw in (None, ""):
            iss.worker_id = None
        else:
            w = db.session.get(Worker, raw)
            if not w:
                return jsonify({"detail": "Funcionario nao encontrado"}), 404
            iss.worker_id = raw

    if "material" in data:
        raw = data.get("material")
        if raw is None:
            iss.material = ""
        elif isinstance(raw, str):
            iss.material = raw.strip()
        else:
            iss.material = str(raw)

    if "quantity" in data:
        raw = data.get("quantity")
        if raw in (None, ""):
            iss.quantity = None
        else:
            fv, err = _num_ge0(raw, "quantity")
            if err:
                return jsonify({"detail": err}), 400
            iss.quantity = fv

    if "hours_spent" in data:
        raw = data.get("hours_spent")
        if raw in (None, ""):
            iss.hours_spent = None
        else:
            fv, err = _num_ge0(raw, "hours_spent")
            if err:
                return jsonify({"detail": err}), 400
            iss.hours_spent = fv

    if "cost" in data:
        raw = data.get("cost")
        if raw in (None, ""):
            iss.cost = None
        else:
            fv, err = _num_ge0(raw, "cost")
            if err:
                return jsonify({"detail": err}), 400
            iss.cost = fv

    if "issue_date" in data:
        raw = data.get("issue_date")
        if raw in (None, ""):
            return jsonify({"detail": "issue_date invalida"}), 400
        try:
            d = parse_date(raw)
        except Exception:
            return jsonify({"detail": "issue_date invalida"}), 400
        if d is None:
            return jsonify({"detail": "issue_date invalida"}), 400
        iss.issue_date = d

    if "reason" in data:
        iss.reason = data.get("reason") or ""
    if "notes" in data:
        iss.notes = data.get("notes") or ""

    db.session.commit()
    return jsonify(iss.to_dict())


@bp.delete("/api/issues/<issue_id>")
@token_required()
def delete_issue(issue_id):
    iss = db.session.get(ProductionIssue, issue_id)
    if not iss:
        return jsonify({"detail": "Ocorrencia nao encontrada"}), 404
    db.session.delete(iss)
    db.session.commit()
    return jsonify({"ok": True})


@bp.get("/api/production/pending")
@token_required()
def pending_overview():
    """Pendencias de producao de TODOS os projetos, opcionalmente num periodo.

    Junta as duas coisas que a spec chama de "pendencias" no modulo Producao:
      - ocorrencias (retrabalho / desperdicio / perda), com o custo somado;
      - itens de checklist ainda nao concluidos.

    O CRUD existente de ocorrencias e por projeto; a aba precisa da visao
    cruzada. Custo de ocorrencia sem valor conta como 0 no total — nao inventa
    numero.
    """
    try:
        de = parse_date(request.args.get("from"))
        ate = parse_date(request.args.get("to"))
    except ValueError:
        return jsonify({"detail": "from/to devem estar em YYYY-MM-DD"}), 400

    q = db.session.query(ProductionIssue)
    if de:
        q = q.filter(ProductionIssue.issue_date >= de)
    if ate:
        q = q.filter(ProductionIssue.issue_date <= ate)
    issues = q.order_by(ProductionIssue.issue_date.desc()).all()

    por_tipo = {k: {"count": 0, "cost": 0.0} for k in sorted(ISSUE_KINDS)}
    total = 0.0
    sem_custo = 0
    for i in issues:
        if i.cost is None:
            sem_custo += 1
        custo = float(i.cost or 0)
        total += custo
        if i.kind in por_tipo:
            por_tipo[i.kind]["count"] += 1
            por_tipo[i.kind]["cost"] += custo

    checklist = (
        db.session.query(ChecklistItem)
        .filter(ChecklistItem.completed.is_(False))
        .order_by(ChecklistItem.project_id, ChecklistItem.position)
        .all()
    )

    return jsonify({
        "period": {"from": iso(de), "to": iso(ate)},
        "issues": [i.to_dict() for i in issues],
        "issues_count": len(issues),
        "issues_total_cost": round(total, 2),
        "issues_without_cost": sem_custo,
        "issues_by_kind": {
            k: {"count": v["count"], "cost": round(v["cost"], 2)}
            for k, v in por_tipo.items()
        },
        "checklist": [
            {
                "id": c.id,
                "project_id": c.project_id,
                "project_title": c.project.title if c.project else None,
                "label": c.label,
                "step_id": c.step_id,
            }
            for c in checklist
        ],
        "checklist_count": len(checklist),
    })
