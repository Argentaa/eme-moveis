from fastapi import APIRouter, Depends

from endpoints.security import require_roles
from schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectStepsUpdate,
    ProjectResponse,
)
from service.project_service import project_service

router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"],
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))],
)


@router.get("/overdue")
async def get_overdue() -> list[dict]:
    """Projetos com deadline vencido, independente do status."""
    return await project_service.get_overdue()


@router.get("", response_model=list[ProjectResponse])
async def get_all() -> list[ProjectResponse]:
    return await project_service.get_all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_by_id(project_id: str) -> ProjectResponse:
    return await project_service.get_by_id(project_id)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=201,
)
async def create(data: ProjectCreate) -> ProjectResponse:
    return await project_service.create(data)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def update(project_id: str, data: ProjectUpdate) -> ProjectResponse:
    return await project_service.update(project_id, data)


@router.put(
    "/{project_id}/steps",
    response_model=ProjectResponse,
)
async def update_steps(
    project_id: str, data: ProjectStepsUpdate
) -> ProjectResponse:
    return await project_service.update_steps(project_id, data)


@router.delete(
    "/{project_id}",
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def delete(project_id: str) -> dict:
    return await project_service.delete(project_id)
