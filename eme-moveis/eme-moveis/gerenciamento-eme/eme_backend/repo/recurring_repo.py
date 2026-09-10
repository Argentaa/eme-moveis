import uuid
from typing import Optional
from datetime import date, timedelta
import calendar
import aiomysql
from repo.connection import get_pool


class RecurringRepo:

    async def create(self, data: dict) -> dict:
        rec_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO recurring_financial
                       (id, description, type, category, amount, frequency,
                        start_date, next_date, project_id, active)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)""",
                    (
                        rec_id,
                        data["description"],
                        data["type"],
                        data["category"],
                        data["amount"],
                        data["frequency"],
                        data["start_date"],
                        data["next_date"],
                        data.get("project_id"),
                    ),
                )
                await cur.execute(
                    "SELECT * FROM recurring_financial WHERE id = %s", (rec_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else {}

    async def find_all_active(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM recurring_financial WHERE active = 1 ORDER BY next_date ASC"
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_due(self) -> list[dict]:
        """Retorna recorrências com next_date <= hoje."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM recurring_financial WHERE active = 1 AND next_date <= CURDATE()"
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def update_next_date(self, rec_id: str, next_date: str) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE recurring_financial SET next_date = %s WHERE id = %s",
                    (next_date, rec_id),
                )

    async def deactivate(self, rec_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE recurring_financial SET active = 0 WHERE id = %s",
                    (rec_id,),
                )
                return cur.rowcount > 0


recurring_repo = RecurringRepo()
