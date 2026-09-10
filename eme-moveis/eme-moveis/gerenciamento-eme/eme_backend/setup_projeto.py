import getpass
import os
import re
import uuid

import bcrypt
import pymysql


def _identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"{label} deve conter apenas letras, números e underscore.")
    return value


def setup() -> None:
    print("=== Configuração rápida do EME Móveis ===")
    print("Este assistente cria as tabelas, opcionalmente cria o usuário MySQL da aplicação e cadastra o primeiro ADMIN.")

    db_name = _identifier(os.getenv("DB_NAME") or "emebd", "DB_NAME")
    app_user = _identifier(os.getenv("DB_USER") or input("Usuário MySQL da aplicação [eme_user]: ").strip() or "eme_user", "DB_USER")
    app_pass = os.getenv("DB_PASSWORD") or getpass.getpass("Senha do usuário MySQL da aplicação: ")

    root_user = input("Usuário raiz do MySQL [root]: ").strip() or "root"
    root_pass = getpass.getpass("Senha raiz do MySQL (deixe em branco se não tiver): ")

    print("\n1. Criando banco, tabelas e permissões...")
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST") or "localhost",
            user=root_user,
            password=root_pass,
            autocommit=True,
        )
        with conn.cursor() as cur:
            with open("init_db.sql", "r", encoding="utf-8") as f:
                sql_script = f.read()
            sql_script = sql_script.replace(
                "CREATE DATABASE IF NOT EXISTS emebd",
                f"CREATE DATABASE IF NOT EXISTS `{db_name}`",
            ).replace("USE emebd;", f"USE `{db_name}`;")

            for query in sql_script.split(";"):
                query = query.strip()
                if query:
                    cur.execute(query)

            cur.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'localhost' IDENTIFIED BY %s", (app_pass,))
            cur.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{app_user}'@'localhost'")
            cur.execute("FLUSH PRIVILEGES")

        conn.close()
        print("Banco, tabelas e usuário da aplicação configurados com sucesso.")
    except Exception as exc:
        print(f"Erro ao configurar o banco: {exc}")
        return

    print("\n2. Criando usuário ADMIN inicial...")
    try:
        admin_id = str(uuid.uuid4())
        username = os.getenv("ADMIN_USERNAME") or input("Login do admin [admin]: ").strip() or "admin"
        name = os.getenv("ADMIN_NAME") or input("Nome do admin [Administrador]: ").strip() or "Administrador"
        email = os.getenv("ADMIN_EMAIL") or input("E-mail do admin [admin@eme.com]: ").strip() or "admin@eme.com"
        password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Senha inicial do admin: ")
        if len(password) < 8:
            print("A senha do admin precisa ter no mínimo 8 caracteres.")
            return

        conn = pymysql.connect(
            host=os.getenv("DB_HOST") or "localhost",
            user=app_user,
            password=app_pass,
            db=db_name,
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                print(f"Usuário '{username}' já existia no banco de dados.")
            else:
                hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cur.execute(
                    """INSERT INTO users (id, username, name, email, role, password)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (admin_id, username, name, email, "ADMIN", hashed),
                )
                print("Usuário ADMIN inserido com sucesso.")
                print(f"Login: {username}")
        conn.close()
        print("\nConfiguração concluída.")
    except Exception as exc:
        print(f"Erro ao inserir o admin: {exc}")


if __name__ == "__main__":
    setup()
