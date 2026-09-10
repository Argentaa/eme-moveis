from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status

from repo.stock_repo import stock_repo
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


class StockService:
    """Lógica de negócio para estoque (itens, categorias, movimentações)."""

    # ── Categorias ──────────────────────────────────────────────

    async def get_categories(self, category_type: Optional[str] = None) -> list[CategoryResponse]:
        rows = await stock_repo.find_all_categories(category_type=category_type)
        return [CategoryResponse(**r) for r in rows]

    async def create_category(self, data: CategoryCreate, requester_role: str = "ADMIN") -> CategoryResponse:
        # ESTOQUE só pode criar categorias de estoque, não financeiras.
        if requester_role == "ESTOQUE" and data.category_type.value != "STOCK":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas categorias de estoque podem ser criadas com este perfil de acesso",
            )

        existing = await stock_repo.find_category_by_name(data.name, category_type=data.category_type.value)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Categoria já cadastrada",
            )

        row = await stock_repo.create_category(
            name=data.name,
            description=data.description,
            category_type=data.category_type.value,
        )
        return CategoryResponse(**row)

    async def update_category(self, category_id: str, data: CategoryUpdate) -> CategoryResponse:
        existing = await stock_repo.find_category_by_id(category_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada",
            )

        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("name") and update_data["name"] != existing["name"]:
            duplicate = await stock_repo.find_category_by_name(
                update_data["name"], category_type=existing["category_type"]
            )
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe uma categoria com este nome",
                )

        # Se o nome mudar, lançamentos financeiros antigos referenciam o nome
        # antigo por texto (não por id) — atualiza-os também, para manter a
        # consistência histórica em vez de "perder" a categoria nos registros já lançados.
        if (
            existing["category_type"] == "FINANCIAL"
            and update_data.get("name")
            and update_data["name"] != existing["name"]
        ):
            await stock_repo.rename_financial_category_in_records(existing["name"], update_data["name"])

        row = await stock_repo.update_category(category_id, update_data)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar categoria",
            )
        return CategoryResponse(**row)

    async def delete_category(self, category_id: str) -> dict:
        existing = await stock_repo.find_category_by_id(category_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada",
            )

        if existing["category_type"] == "STOCK":
            items_count = await stock_repo.count_items_in_category(category_id)
            if items_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Não é possível excluir: {items_count} item(ns) de estoque usam esta categoria. "
                           "Mova ou exclua esses itens primeiro.",
                )
        else:
            records_count = await stock_repo.count_financial_records_using_category(existing["name"])
            if records_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Não é possível excluir: {records_count} lançamento(s) financeiro(s) usam esta categoria.",
                )

        deleted = await stock_repo.delete_category(category_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada",
            )
        return {"message": "Categoria removida com sucesso"}

    # ── Itens ───────────────────────────────────────────────────

    async def get_all_items(self) -> list[StockItemResponse]:
        rows = await stock_repo.find_all_items()
        return [StockItemResponse(**r) for r in rows]

    async def create_item(self, data: StockItemCreate) -> StockItemResponse:
        category = await stock_repo.find_category_by_id(data.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Categoria do item não encontrada",
            )

        existing_sku = await stock_repo.find_item_by_sku(data.sku)
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU já cadastrado",
            )

        row = await stock_repo.create_item(
            name=data.name,
            sku=data.sku,
            category_id=data.category_id,
            quantity=data.quantity,
            min_quantity=data.min_quantity,
            unit=data.unit,
            price=data.price,
            supplier=data.supplier,
        )
        return StockItemResponse(**row)

    async def update_item(
        self, item_id: str, data: StockItemUpdate
    ) -> StockItemResponse:
        existing = await stock_repo.find_item_by_id(item_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de estoque não encontrado",
            )
        update_data = data.model_dump(exclude_unset=True)
        if "category_id" in update_data and update_data["category_id"]:
            category = await stock_repo.find_category_by_id(update_data["category_id"])
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Categoria do item não encontrada",
                )

        if "sku" in update_data and update_data["sku"]:
            duplicate = await stock_repo.find_item_by_sku(update_data["sku"])
            if duplicate and duplicate["id"] != item_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="SKU já cadastrado para outro item",
                )

        row = await stock_repo.update_item(item_id, update_data)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar item",
            )
        return StockItemResponse(**row)

    async def delete_item(self, item_id: str) -> dict:
        deleted = await stock_repo.delete_item(item_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de estoque não encontrado",
            )
        return {"message": "Item removido com sucesso"}

    # ── Movimentações ───────────────────────────────────────────

    async def get_movements(self) -> list[StockMovementResponse]:
        rows = await stock_repo.find_all_movements()
        return [StockMovementResponse(**r) for r in rows]

    async def create_movement(
        self, data: StockMovementCreate, user_name: str
    ) -> StockMovementResponse:
        # Verifica se o item existe
        item = await stock_repo.find_item_by_id(data.item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de estoque não encontrado",
            )

        if data.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A quantidade da movimentação deve ser maior que zero",
            )

        quantity = Decimal(str(data.quantity))
        current_quantity = Decimal(str(item["quantity"]))
        delta = quantity if data.type.value == "ENTRADA" else -quantity

        # Valida se não ficará negativo em saída
        new_qty = current_quantity + delta
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estoque insuficiente. Disponível: {item['quantity']}",
            )

        # Atualiza a quantidade do item
        await stock_repo.update_item_quantity(data.item_id, delta)

        # Registra a movimentação
        row = await stock_repo.create_movement(
            item_id=data.item_id,
            movement_type=data.type.value,
            quantity=quantity,
            reason=data.reason,
            created_by=user_name,
        )
        return StockMovementResponse(**row)


stock_service = StockService()
