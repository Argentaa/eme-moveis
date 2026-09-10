from fastapi import HTTPException, status

from repo.client_repo import client_repo
from repo.project_repo import project_repo
from schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectStepsUpdate,
    ProjectResponse,
)


class ProjectService:
    """Lógica de negócio para projetos."""

    async def get_all(self) -> list[ProjectResponse]:
        rows = await project_repo.find_all()
        return [ProjectResponse(**r) for r in rows]

    async def get_by_id(self, project_id: str) -> ProjectResponse:
        row = await project_repo.find_by_id(project_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado",
            )
        return ProjectResponse(**row)

    async def create(self, data: ProjectCreate) -> ProjectResponse:
        client = await client_repo.find_by_id(data.client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente vinculado ao projeto não encontrado",
            )

        steps_dicts = [s.model_dump() for s in data.steps]
        row = await project_repo.create(
            title=data.title,
            client_id=data.client_id,
            description=data.description,
            status=data.status.value,
            value=data.value,
            deadline=data.deadline,
            steps=steps_dicts,
        )
        return ProjectResponse(**row)

    async def update(self, project_id: str, data: ProjectUpdate) -> ProjectResponse:
        existing = await project_repo.find_by_id(project_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado",
            )
        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]
        if "client_id" in update_data and update_data["client_id"]:
            client = await client_repo.find_by_id(update_data["client_id"])
            if client is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cliente vinculado ao projeto não encontrado",
                )
        row = await project_repo.update(project_id, update_data)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar projeto",
            )
        return ProjectResponse(**row)

    async def update_steps(
        self, project_id: str, data: ProjectStepsUpdate
    ) -> ProjectResponse:
        existing = await project_repo.find_by_id(project_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado",
            )
        steps_dicts = [s.model_dump() for s in data.steps]
        row = await project_repo.update_steps(project_id, steps_dicts)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar etapas",
            )
        return ProjectResponse(**row)

    async def delete(self, project_id: str) -> dict:
        deleted = await project_repo.delete(project_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado",
            )
        return {"message": "Projeto removido com sucesso"}


    async def get_overdue(self) -> list[dict]:
        """Projetos com deadline vencido, com dias de atraso calculados."""
        rows = await project_repo.find_overdue()
        result = []
        for r in rows:
            row = dict(r)
            for key, val in row.items():
                if hasattr(val, 'isoformat'):
                    row[key] = val.isoformat() if hasattr(val, 'hour') else str(val)
            result.append(row)
        return result


project_service = ProjectService()
