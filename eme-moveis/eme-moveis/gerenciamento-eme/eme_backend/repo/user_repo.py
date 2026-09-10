import uuid
from typing import Optional

import aiomysql

from repo.connection import get_pool


class UserRepo:
    """Comunicação com a tabela `users` — queries parametrizadas."""

    async def find_by_username(self, username: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM users WHERE id = %s",
                    (user_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_by_email(self, email: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM users WHERE email = %s",
                    (email,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_all(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT id, username, name, email, role, avatar FROM users"
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def create(
        self,
        username: str,
        name: str,
        email: str,
        role: str,
        hashed_password: str,
        avatar: Optional[str] = None,
    ) -> dict:
        user_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO users (id, username, name, email, role, password, avatar)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (user_id, username, name, email, role, hashed_password, avatar),
                )
        return {
            "id": user_id,
            "username": username,
            "name": name,
            "email": email,
            "role": role,
            "avatar": avatar,
        }

    async def update_role(self, user_id: str, role: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET role = %s WHERE id = %s",
                    (role, user_id),
                )
                return cur.rowcount > 0

    async def delete(self, user_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM users WHERE id = %s",
                    (user_id,),
                )
                return cur.rowcount > 0


user_repo = UserRepo()
