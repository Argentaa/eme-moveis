from fastapi import APIRouter, Depends
from endpoints.security import require_roles
from schemas.recurring import FinancialCreateExtended, RecurringResponse
from service.recurring_service import recurring_service

router = APIRouter(
    prefix="/api/financial/recurring",
    tags=["Recurring Financial"],
    dependencies=[Depends(require_roles("ADMIN", "GERENTE"))],
)

@router.post("")
async def create_extended(data: FinancialCreateExtended) -> dict:
    """Cria lançamento normal, parcelado ou fixo/recorrente."""
    return await recurring_service.create_extended(data)

@router.get("")
async def get_recurring() -> list[dict]:
    """Lista todas as recorrências ativas."""
    return await recurring_service.get_recurring()

@router.delete("/{rec_id}")
async def deactivate(rec_id: str) -> dict:
    """Cancela uma recorrência ativa."""
    return await recurring_service.deactivate(rec_id)

@router.post("/process-due",
             dependencies=[Depends(require_roles("ADMIN", "GERENTE"))])
async def process_due() -> dict:
    """Gera lançamentos das recorrências vencidas. Chamar diariamente."""
    return await recurring_service.process_due()
