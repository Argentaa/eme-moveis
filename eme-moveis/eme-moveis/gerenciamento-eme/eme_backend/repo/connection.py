import aiomysql
from config import settings

_pool: aiomysql.Pool | None = None


async def get_pool() -> aiomysql.Pool:
    """Retorna (ou cria) o pool de conexões MySQL."""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=True,
            charset="utf8mb4",
            minsize=1,
            maxsize=10,
        )
    return _pool


async def close_pool() -> None:
    """Fecha o pool de conexões."""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
