"""
Script utilitário para criar o primeiro usuário ADMIN no banco de dados.
Executar uma única vez após rodar o init_db.sql no MySQL.

Uso:
    python create_admin.py
"""
import asyncio
import getpass
import os
import uuid

import bcrypt

from repo.connection import get_pool, close_pool


async def main() -> None:
    pool = await get_pool()

    admin_id = str(uuid.uuid4())
    username = os.getenv("ADMIN_USERNAME") or input("Login do admin [admin]: ").strip() or "admin"
    name = os.getenv("ADMIN_NAME") or input("Nome do admin [Administrador]: ").strip() or "Administrador"
    email = os.getenv("ADMIN_EMAIL") or input("E-mail do admin [admin@eme.com]: ").strip() or "admin@eme.com"
    role = "ADMIN"
    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Senha inicial do admin: ")
    if len(password) < 8:
        print("A senha precisa ter no mínimo 8 caracteres.")
        await close_pool()
        return

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if await cur.fetchone():
                print(f"Usuário '{username}' já existe. Nenhum registro foi criado.")
                await close_pool()
                return

            await cur.execute(
                """INSERT INTO users (id, username, name, email, role, password)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (admin_id, username, name, email, role, hashed),
            )
    print(f"Usuário ADMIN criado com sucesso! ID: {admin_id}")
    print(f"Login: {username}")
    print("Troque a senha após o primeiro login, se ela foi definida como temporária.")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
