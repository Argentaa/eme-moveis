from fastapi import HTTPException, status

from repo.client_repo import client_repo
from schemas.client import ClientCreate, ClientUpdate, ClientResponse


class ClientService:
    """Lógica de negócio para clientes."""

    async def get_all(self) -> list[ClientResponse]:
        rows = await client_repo.find_all()
        return [ClientResponse(**r) for r in rows]

    async def get_by_id(self, client_id: str) -> ClientResponse:
        row = await client_repo.find_by_id(client_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado",
            )
        return ClientResponse(**row)

    async def create(self, data: ClientCreate) -> ClientResponse:
        existing = await client_repo.find_by_cpf_cnpj(data.cpf_cnpj)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPF/CNPJ já cadastrado",
            )

        row = await client_repo.create(
            name=data.name,
            email=data.email or "",
            phone=data.phone or "",
            cpf_cnpj=data.cpf_cnpj,
            address=data.address or "",
            funnel_status=data.funnel_status.value if hasattr(data.funnel_status, 'value') else (data.funnel_status or "PROSPECCAO"),
            lost_reason=data.lost_reason,
            estimated_value=data.estimated_value,
            lead_source=data.lead_source,
        )
        return ClientResponse(**row)

    async def update(self, client_id: str, data: ClientUpdate) -> ClientResponse:
        existing = await client_repo.find_by_id(client_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado",
            )
        update_data = data.model_dump(exclude_unset=True)
        if "funnel_status" in update_data and update_data["funnel_status"] is not None:
            val = update_data["funnel_status"]
            update_data["funnel_status"] = val.value if hasattr(val, "value") else val
        # lost_reason pode ser string vazia ou None — passa direto

        if "cpf_cnpj" in update_data and update_data["cpf_cnpj"]:
            duplicate = await client_repo.find_by_cpf_cnpj(update_data["cpf_cnpj"])
            if duplicate and duplicate["id"] != client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CPF/CNPJ já cadastrado para outro cliente",
                )

        row = await client_repo.update(client_id, update_data)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar cliente",
            )
        return ClientResponse(**row)

    async def delete(self, client_id: str) -> dict:
        deleted = await client_repo.delete(client_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado",
            )
        return {"message": "Cliente removido com sucesso"}


client_service = ClientService()
