from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from endpoints.security import require_roles
from schemas.financial import (
    FinancialRecordCreate,
    FinancialRecordUpdate,
    FinancialRecordResponse,
)
from service.financial_service import financial_service
from service.receipt_service import receipt_service
from service.pdf_receipt_generator import gerar_recibo_pdf
from service.docx_receipt_generator import gerar_recibo_docx

router = APIRouter(
    prefix="/api/financial",
    tags=["Financial"],
    dependencies=[Depends(require_roles("ADMIN", "GERENTE"))],
)


@router.get("", response_model=list[FinancialRecordResponse])
async def get_all() -> list[FinancialRecordResponse]:
    return await financial_service.get_all()


@router.get("/upcoming")
async def get_upcoming(days: int = 7) -> dict:
    """Lançamentos pendentes nos próximos N dias."""
    return await financial_service.get_upcoming(days=days)


@router.get("/overdue")
async def get_overdue() -> dict:
    """Lançamentos de entrada pendentes e já vencidos, agrupados por cliente e projeto."""
    return await financial_service.get_overdue_grouped()


@router.post("", response_model=FinancialRecordResponse, status_code=201)
async def create(data: FinancialRecordCreate) -> FinancialRecordResponse:
    return await financial_service.create(data)


@router.put(
    "/{record_id}",
    response_model=FinancialRecordResponse,
    dependencies=[Depends(require_roles("ADMIN", "GERENTE"))],
)
async def update(
    record_id: str, data: FinancialRecordUpdate
) -> FinancialRecordResponse:
    return await financial_service.update(record_id, data)


@router.delete(
    "/{record_id}",
    dependencies=[Depends(require_roles("ADMIN", "GERENTE"))],
)
async def delete(record_id: str) -> dict:
    return await financial_service.delete(record_id)


@router.get("/{record_id}/receipt")
async def get_receipt(record_id: str, format: Literal["pdf", "docx"] = "pdf") -> Response:
    """Gera e retorna o recibo do lançamento financeiro em PDF ou DOCX."""
    data = await receipt_service.build_receipt_data(record_id)

    if format == "pdf":
        content = gerar_recibo_pdf(data)
        media_type = "application/pdf"
        extension = "pdf"
    elif format == "docx":
        content = gerar_recibo_docx(data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Utilize 'pdf' ou 'docx'.",
        )

    filename = f"recibo-{record_id[:8]}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
