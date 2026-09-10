import json
import uuid
from typing import Optional

import aiomysql

from repo.connection import get_pool

# Colunas permitidas para atualização (previne injeção de nomes de coluna)
_ALLOWED_COLUMNS = frozenset({
    "title", "client_id", "description", "status", "value", "deadline",
})


class ProjectRepo:
    """Comunicação com a tabela `projects` — queries parametrizadas."""

    async def find_all(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT p.*, c.name AS client_name
                       FROM projects p
                       LEFT JOIN clients c ON p.client_id = c.id
                       ORDER BY p.created_at DESC"""
                )
                rows = await cur.fetchall()
                result: list[dict] = []
                for r in rows:
                    row = dict(r)
                    row["steps"] = json.loads(row["steps"]) if row.get("steps") else []
                    result.append(row)
                return result

    async def find_by_id(self, project_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT p.*, c.name AS client_name
                       FROM projects p
                       LEFT JOIN clients c ON p.client_id = c.id
                       WHERE p.id = %s""",
                    (project_id,),
                )
                row = await cur.fetchone()
                if row is None:
                    return None
                result = dict(row)
                result["steps"] = json.loads(result["steps"]) if result.get("steps") else []
                return result

    async def create(
        self,
        title: str,
        client_id: str,
        description: str,
        status: str,
        value: float,
        deadline: str,
        steps: list[dict],
    ) -> dict:
        project_id = str(uuid.uuid4())
        steps_json = json.dumps(steps, ensure_ascii=False)
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO projects
                       (id, title, client_id, description, status, value, deadline, steps, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                    (project_id, title, client_id, description, status, value, deadline, steps_json),
                )
        return await self.find_by_id(project_id) or {}

    async def update(self, project_id: str, data: dict) -> Optional[dict]:
        if not data:
            return await self.find_by_id(project_id)

        # Filtra apenas colunas permitidas para prevenir injeção
        safe_data = {k: v for k, v in data.items() if k in _ALLOWED_COLUMNS}
        if not safe_data:
            return await self.find_by_id(project_id)

        set_clauses: list[str] = []
        values: list[object] = []
        for key, value in safe_data.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        values.append(project_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = %s",
                    tuple(values),
                )
        return await self.find_by_id(project_id)

    async def update_steps(self, project_id: str, steps: list[dict]) -> Optional[dict]:
        steps_json = json.dumps(steps, ensure_ascii=False)
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "UPDATE projects SET steps = %s WHERE id = %s",
                    (steps_json, project_id),
                )
        return await self.find_by_id(project_id)

    async def delete(self, project_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM projects WHERE id = %s",
                    (project_id,),
                )
                return cur.rowcount > 0


    async def find_overdue(self) -> list[dict]:
        """Projetos com deadline vencido independente do status."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT p.*, c.name AS client_name,
                              DATEDIFF(CURDATE(), p.deadline) AS days_overdue
                       FROM projects p
                       LEFT JOIN clients c ON p.client_id = c.id
                       WHERE p.deadline < CURDATE()
                       ORDER BY p.deadline ASC"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


project_repo = ProjectRepo()
