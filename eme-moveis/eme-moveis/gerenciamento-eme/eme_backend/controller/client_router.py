from fastapi import APIRouter, Depends

from endpoints.security import require_roles
from schemas.client import ClientCreate, ClientUpdate, ClientResponse
from service.client_service import client_service

router = APIRouter(
    prefix="/api/clients",
    tags=["Clients"],
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))],
)


@router.get("", response_model=list[ClientResponse])
async def get_all() -> list[ClientResponse]:
    return await client_service.get_all()


@router.get("/{client_id}", response_model=ClientResponse)
async def get_by_id(client_id: str) -> ClientResponse:
    return await client_service.get_by_id(client_id)


@router.post(
    "",
    response_model=ClientResponse,
    status_code=201,
)
async def create(data: ClientCreate) -> ClientResponse:
    return await client_service.create(data)


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
)
async def update(client_id: str, data: ClientUpdate) -> ClientResponse:
    return await client_service.update(client_id, data)


@router.delete(
    "/{client_id}",
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def delete(client_id: str) -> dict:
    return await client_service.delete(client_id)
