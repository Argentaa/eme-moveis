from typing import Optional

from fastapi import APIRouter, Depends

from endpoints.security import get_current_user, require_roles
from schemas.stock import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    StockItemCreate,
    StockItemUpdate,
    StockItemResponse,
    StockMovementCreate,
    StockMovementResponse,
)
from schemas.user import TokenData
from service.stock_service import stock_service

router = APIRouter(
    prefix="/api/stock",
    tags=["Stock"],
    dependencies=[Depends(get_current_user)],
)


# ── Itens ───────────────────────────────────────────────────

@router.get("", response_model=list[StockItemResponse])
async def get_all_items() -> list[StockItemResponse]:
    return await stock_service.get_all_items()


@router.post(
    "",
    response_model=StockItemResponse,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "ESTOQUE", "PROJETISTA"))],
)
async def create_item(data: StockItemCreate) -> StockItemResponse:
    return await stock_service.create_item(data)


@router.put(
    "/{item_id}",
    response_model=StockItemResponse,
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "ESTOQUE", "PROJETISTA"))],
)
async def update_item(item_id: str, data: StockItemUpdate) -> StockItemResponse:
    return await stock_service.update_item(item_id, data)


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))],
)
async def delete_item(item_id: str) -> dict:
    return await stock_service.delete_item(item_id)


# ── Movimentações ───────────────────────────────────────────

@router.get("/movements/history", response_model=list[StockMovementResponse])
async def get_movements() -> list[StockMovementResponse]:
    return await stock_service.get_movements()


@router.post(
    "/movements",
    response_model=StockMovementResponse,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "ESTOQUE", "PROJETISTA"))],
)
async def create_movement(
    data: StockMovementCreate,
    current_user: TokenData = Depends(get_current_user),
) -> StockMovementResponse:
    return await stock_service.create_movement(data, current_user.username)


# ── Categorias (de Estoque e Financeiras) ────────────────────
# Mesma tabela para os dois contextos, diferenciados por category_type.
# Gerenciamento (criar/editar/excluir) restrito a ADMIN/GERENTE.

@router.get("/categories/all", response_model=list[CategoryResponse])
async def get_categories(category_type: Optional[str] = None) -> list[CategoryResponse]:
    return await stock_service.get_categories(category_type=category_type)


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "ESTOQUE", "PROJETISTA"))],
)
async def create_category(
    data: CategoryCreate,
    current_user: TokenData = Depends(get_current_user),
) -> CategoryResponse:
    return await stock_service.create_category(data, current_user.role)


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))],
)
async def update_category(category_id: str, data: CategoryUpdate) -> CategoryResponse:
    return await stock_service.update_category(category_id, data)


@router.delete(
    "/categories/{category_id}",
    dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))],
)
async def delete_category(category_id: str) -> dict:
    return await stock_service.delete_category(category_id)
