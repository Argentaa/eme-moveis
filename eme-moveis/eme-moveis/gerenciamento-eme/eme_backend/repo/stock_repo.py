import uuid
from typing import Optional

import aiomysql

from repo.connection import get_pool

# Colunas permitidas para atualização (previne injeção de nomes de coluna)
_ALLOWED_ITEM_COLUMNS = frozenset({
    "name", "sku", "category_id", "quantity", "min_quantity", "unit", "price", "supplier",
})


class StockRepo:
    """Comunicação com as tabelas de estoque — queries parametrizadas."""

    # ── Categorias ──────────────────────────────────────────────

    async def find_all_categories(self, category_type: Optional[str] = None) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if category_type:
                    await cur.execute(
                        "SELECT * FROM categories WHERE category_type = %s ORDER BY name",
                        (category_type,),
                    )
                else:
                    await cur.execute("SELECT * FROM categories ORDER BY category_type, name")
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_category_by_id(self, category_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM categories WHERE id = %s",
                    (category_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_category_by_name(self, name: str, category_type: str = "STOCK") -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM categories WHERE name = %s AND category_type = %s",
                    (name, category_type),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def create_category(
        self, name: str, description: Optional[str] = None, category_type: str = "STOCK"
    ) -> dict:
        cat_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "INSERT INTO categories (id, name, description, category_type) VALUES (%s, %s, %s, %s)",
                    (cat_id, name, description, category_type),
                )
        return await self.find_category_by_id(cat_id) or {}

    async def update_category(self, category_id: str, data: dict) -> Optional[dict]:
        safe_data = {k: v for k, v in data.items() if k in ("name", "description")}
        if not safe_data:
            return await self.find_category_by_id(category_id)

        set_clauses = [f"`{key}` = %s" for key in safe_data]
        values = list(safe_data.values())
        values.append(category_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"UPDATE categories SET {', '.join(set_clauses)} WHERE id = %s",
                    tuple(values),
                )
        return await self.find_category_by_id(category_id)

    async def delete_category(self, category_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM categories WHERE id = %s", (category_id,))
                return cur.rowcount > 0

    async def count_items_in_category(self, category_id: str) -> int:
        """Quantos itens de estoque usam esta categoria (para impedir exclusão indevida)."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM stock_items WHERE category_id = %s",
                    (category_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else 0

    async def count_financial_records_using_category(self, category_name: str) -> int:
        """Quantos lançamentos financeiros usam esta categoria pelo nome."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM financial_records WHERE category = %s",
                    (category_name,),
                )
                row = await cur.fetchone()
                return row[0] if row else 0

    async def rename_financial_category_in_records(self, old_name: str, new_name: str) -> None:
        """Atualiza o texto da categoria nos lançamentos já existentes após uma renomeação."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE financial_records SET category = %s WHERE category = %s",
                    (new_name, old_name),
                )

    # ── Itens de estoque ────────────────────────────────────────

    async def find_all_items(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT s.*, c.name AS category_name
                       FROM stock_items s
                       LEFT JOIN categories c ON s.category_id = c.id
                       ORDER BY s.name"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_item_by_id(self, item_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT s.*, c.name AS category_name
                       FROM stock_items s
                       LEFT JOIN categories c ON s.category_id = c.id
                       WHERE s.id = %s""",
                    (item_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_item_by_sku(self, sku: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM stock_items WHERE sku = %s",
                    (sku,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def create_item(
        self,
        name: str,
        sku: str,
        category_id: str,
        quantity: float,
        min_quantity: float,
        unit: str,
        price: float,
        supplier: str,
    ) -> dict:
        item_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO stock_items
                       (id, name, sku, category_id, quantity, min_quantity, unit, price, supplier)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (item_id, name, sku, category_id, quantity, min_quantity, unit, price, supplier),
                )
        return await self.find_item_by_id(item_id) or {}

    async def update_item(self, item_id: str, data: dict) -> Optional[dict]:
        if not data:
            return await self.find_item_by_id(item_id)

        # Filtra apenas colunas permitidas para prevenir injeção
        safe_data = {k: v for k, v in data.items() if k in _ALLOWED_ITEM_COLUMNS}
        if not safe_data:
            return await self.find_item_by_id(item_id)

        set_clauses: list[str] = []
        values: list[object] = []
        for key, value in safe_data.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        values.append(item_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    f"UPDATE stock_items SET {', '.join(set_clauses)} WHERE id = %s",
                    tuple(values),
                )
        return await self.find_item_by_id(item_id)

    async def delete_item(self, item_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM stock_items WHERE id = %s",
                    (item_id,),
                )
                return cur.rowcount > 0

    async def update_item_quantity(self, item_id: str, delta: float) -> None:
        """Incrementa ou decrementa a quantidade de um item de estoque."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE stock_items SET quantity = quantity + %s WHERE id = %s",
                    (delta, item_id),
                )

    # ── Movimentações ───────────────────────────────────────────

    async def find_all_movements(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT m.*, s.name AS item_name
                       FROM stock_movements m
                       LEFT JOIN stock_items s ON m.item_id = s.id
                       ORDER BY m.date DESC"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def create_movement(
        self,
        item_id: str,
        movement_type: str,
        quantity: float,
        reason: str,
        created_by: str,
    ) -> dict:
        mov_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO stock_movements
                       (id, item_id, type, quantity, reason, created_by, date)
                       VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                    (mov_id, item_id, movement_type, quantity, reason, created_by),
                )
                await cur.execute(
                    """SELECT m.*, s.name AS item_name
                       FROM stock_movements m
                       LEFT JOIN stock_items s ON m.item_id = s.id
                       WHERE m.id = %s""",
                    (mov_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else {}


stock_repo = StockRepo()
