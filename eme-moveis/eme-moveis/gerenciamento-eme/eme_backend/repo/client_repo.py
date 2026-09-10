import uuid
from typing import Optional

import aiomysql

from repo.connection import get_pool

# Colunas permitidas para atualização (previne injeção de nomes de coluna)
_ALLOWED_COLUMNS = frozenset({"name", "email", "phone", "cpf_cnpj", "address", "funnel_status", "lost_reason", "estimated_value", "lead_source"})


class ClientRepo:
    """Comunicação com a tabela `clients` — queries parametrizadas."""

    async def find_all(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM clients ORDER BY created_at DESC")
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_by_id(self, client_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM clients WHERE id = %s",
                    (client_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_by_cpf_cnpj(self, cpf_cnpj: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM clients WHERE cpf_cnpj = %s",
                    (cpf_cnpj,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_by_email(self, email: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM clients WHERE email = %s",
                    (email,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def create(
        self,
        name: str,
        email: str,
        phone: str,
        cpf_cnpj: str,
        address: str,
        funnel_status: str = "PROSPECCAO",
        lost_reason: str = None,
        estimated_value: float = None,
        lead_source: str = None,
    ) -> dict:
        client_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO clients (id, name, email, phone, cpf_cnpj, address, funnel_status, lost_reason, estimated_value, lead_source, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                    (client_id, name, email, phone, cpf_cnpj, address, funnel_status, lost_reason, estimated_value, lead_source),
                )
                await cur.execute(
                    "SELECT * FROM clients WHERE id = %s", (client_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else {}

    async def update(self, client_id: str, data: dict) -> Optional[dict]:
        if not data:
            return await self.find_by_id(client_id)

        # Filtra apenas colunas permitidas para prevenir injeção
        safe_data = {k: v for k, v in data.items() if k in _ALLOWED_COLUMNS}
        if not safe_data:
            return await self.find_by_id(client_id)

        set_clauses: list[str] = []
        values: list[object] = []
        for key, value in safe_data.items():
            set_clauses.append(f"`{key}` = %s")
            values.append(value)
        values.append(client_id)

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    f"UPDATE clients SET {', '.join(set_clauses)} WHERE id = %s",
                    tuple(values),
                )
                await cur.execute(
                    "SELECT * FROM clients WHERE id = %s", (client_id,)
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def delete(self, client_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM clients WHERE id = %s",
                    (client_id,),
                )
                return cur.rowcount > 0


client_repo = ClientRepo()
