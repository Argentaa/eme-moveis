from fastapi import HTTPException, status

from repo.financial_repo import financial_repo
from repo.project_repo import project_repo
from repo.stock_repo import stock_repo
from schemas.financial import (
    FinancialRecordCreate,
    FinancialRecordUpdate,
    FinancialRecordResponse,
)


class FinancialService:
    """Lógica de negócio para registros financeiros."""

    async def get_all(self) -> list[FinancialRecordResponse]:
        rows = await financial_repo.find_all()
        return [FinancialRecordResponse(**r) for r in rows]

    async def _validate_category(self, category_name: str) -> None:
        category = await stock_repo.find_category_by_name(category_name, category_type="FINANCIAL")
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Categoria financeira '{category_name}' não existe. "
                       "Cadastre-a em Acessos & TI > Categorias antes de usá-la.",
            )

    async def create(self, data: FinancialRecordCreate) -> FinancialRecordResponse:
        if data.project_id:
            project = await project_repo.find_by_id(data.project_id)
            if project is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Projeto vinculado ao lançamento financeiro não encontrado",
                )

        await self._validate_category(data.category)

        row = await financial_repo.create(
            description=data.description,
            record_type=data.type.value,
            category=data.category,
            amount=data.amount,
            date=data.date,
            due_date=data.due_date,
            status=data.status.value,
            project_id=data.project_id,
        )
        return FinancialRecordResponse(**row)

    async def update(
        self, record_id: str, data: FinancialRecordUpdate
    ) -> FinancialRecordResponse:
        existing = await financial_repo.find_by_id(record_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro financeiro não encontrado",
            )
        update_data = data.model_dump(exclude_unset=True)
        # Converter enums (type, status) para seus valores string
        for key in ("type", "status"):
            if key in update_data and update_data[key] is not None:
                val = update_data[key]
                update_data[key] = val.value if hasattr(val, "value") else val
        if update_data.get("category"):
            await self._validate_category(update_data["category"])
        if update_data.get("project_id"):
            project = await project_repo.find_by_id(update_data["project_id"])
            if project is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Projeto vinculado ao lançamento financeiro não encontrado",
                )
        row = await financial_repo.update(record_id, update_data)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar registro",
            )
        return FinancialRecordResponse(**row)

    async def delete(self, record_id: str) -> dict:
        deleted = await financial_repo.delete(record_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro financeiro não encontrado",
            )
        return {"message": "Registro removido com sucesso"}


    async def get_overdue_grouped(self) -> dict:
        """Agrupa lançamentos vencidos (ENTRADA, PENDENTE, vencimento < hoje)
        por cliente, com subtotal por projeto e total geral."""
        rows = await financial_repo.find_overdue()

        clients_map: dict[str, dict] = {}
        no_client_key = "__sem_cliente__"

        for row in rows:
            client_id = row.get("client_id") or no_client_key
            client_name = row.get("client_name") or "Sem cliente vinculado"

            if client_id not in clients_map:
                clients_map[client_id] = {
                    "client_id": row.get("client_id"),
                    "client_name": client_name,
                    "total_overdue": 0.0,
                    "projects": {},
                }

            project_id = row.get("project_id") or "__sem_projeto__"
            project_title = row.get("project_title") or "Sem projeto vinculado"

            if project_id not in clients_map[client_id]["projects"]:
                clients_map[client_id]["projects"][project_id] = {
                    "project_id": row.get("project_id"),
                    "project_title": project_title,
                    "subtotal": 0.0,
                    "records": [],
                }

            amount = float(row["amount"])
            clients_map[client_id]["total_overdue"] += amount
            clients_map[client_id]["projects"][project_id]["subtotal"] += amount
            clients_map[client_id]["projects"][project_id]["records"].append({
                "id": row["id"],
                "description": row["description"],
                "amount": amount,
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
            })

        clients_list = []
        for client_data in clients_map.values():
            client_data["projects"] = list(client_data["projects"].values())
            clients_list.append(client_data)

        clients_list.sort(key=lambda c: c["total_overdue"], reverse=True)

        return {
            "clients": clients_list,
            "grand_total": sum(c["total_overdue"] for c in clients_list),
        }


    async def get_upcoming(self, days: int = 7) -> dict:
        """Lançamentos pendentes nos próximos N dias, separados por tipo."""
        rows = await financial_repo.find_upcoming(days=days)
        result = []
        for r in rows:
            row = dict(r)
            for key, val in row.items():
                if hasattr(val, 'isoformat'):
                    row[key] = str(val)
            result.append(row)

        receivables = [r for r in result if r["type"] == "ENTRADA"]
        payables = [r for r in result if r["type"] == "SAIDA"]

        return {
            "receivables": receivables,
            "payables": payables,
            "total_receivables": sum(float(r["amount"]) for r in receivables),
            "total_payables": sum(float(r["amount"]) for r in payables),
            "days": days,
        }


financial_service = FinancialService()
