import uuid
from typing import Optional

import aiomysql

from repo.connection import get_pool

# Colunas permitidas para atualização (previne injeção de nomes de coluna)
_ALLOWED_COLUMNS = frozenset({
    "description", "type", "category", "amount", "date", "due_date", "project_id", "status",
})


class FinancialRepo:
    """Comunicação com a tabela `financial_records` — queries parametrizadas."""

    async def find_all(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM financial_records ORDER BY date DESC"
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_by_id(self, record_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM financial_records WHERE id = %s",
                    (record_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def create(
        self,
        description: str,
        record_type: str,
        category: str,
        amount: float,
        date: str,
        due_date: str,
        status: str,
        project_id: Optional[str] = None,
    ) -> dict:
        record_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO financial_records
                       (id, description, type, category, amount, date, due_date, project_id, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (record_id, description, record_type, category, amount, date, due_date, project_id, status),
                )
                await cur.execute(
                    "SELECT * FROM financial_records WHERE id = %s",
                    (record_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else {}

    async def update(self, record_id: str, data: dict) -> Optional[dict]:
        if not data:
            return await self.find_by_id(record_id)

        # Filtra apenas colunas permitidas para prevenir injeção
        safe_data = {k: v for k, v in data.items() if k in _ALLOWED_COLUMNS}
        if not safe_data:
            return await self.find_by_id(record_id)

        set_clauses: list[str] = []
        values: list[object] = []
        for key, value in safe_data.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        values.append(record_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    f"UPDATE financial_records SET {', '.join(set_clauses)} WHERE id = %s",
                    tuple(values),
                )
                await cur.execute(
                    "SELECT * FROM financial_records WHERE id = %s",
                    (record_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def delete(self, record_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM financial_records WHERE id = %s",
                    (record_id,),
                )
                return cur.rowcount > 0


    async def find_overdue(self) -> list[dict]:
        """Lançamentos do tipo ENTRADA, PENDENTE e com vencimento já passado,
        já trazendo o nome do cliente e do projeto associado."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT f.id, f.description, f.amount, f.date, f.status,
                              f.project_id, p.title AS project_title,
                              p.client_id, c.name AS client_name
                       FROM financial_records f
                       LEFT JOIN projects p ON f.project_id = p.id
                       LEFT JOIN clients c ON p.client_id = c.id
                       WHERE f.type = 'ENTRADA'
                         AND f.status = 'PENDENTE'
                         AND f.date < CURDATE()
                       ORDER BY c.name, f.date ASC"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


    async def find_upcoming(self, days: int = 7) -> list[dict]:
        """Lançamentos PENDENTES com vencimento nos próximos N dias."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT f.*, c.name AS client_name, p.title AS project_title
                       FROM financial_records f
                       LEFT JOIN projects p ON f.project_id = p.id
                       LEFT JOIN clients c ON p.client_id = c.id
                       WHERE f.status = 'PENDENTE'
                         AND f.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
                       ORDER BY f.due_date ASC""",
                    (days,)
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


financial_repo = FinancialRepo()
