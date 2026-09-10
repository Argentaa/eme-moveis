from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from endpoints.security import get_current_user, require_roles
from repo.connection import get_pool
import aiomysql
import uuid

router = APIRouter(
    prefix="/api/funnel-columns",
    tags=["Funnel Columns"],
    dependencies=[Depends(get_current_user)],
)

class FunnelColumnUpdate(BaseModel):
    label: str
    description: Optional[str] = None


@router.get("")
async def get_all(type: str = "CRM") -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if type == "PROJECTS":
                order = "FIELD(column_key, 'ORCAMENTO','PROJETADO','PRODUCAO','MONTAGEM','CONCLUIDO')"
            else:
                order = "FIELD(column_key, 'PROSPECCAO','ORCAMENTO','APRESENTACAO','NEGOCIACAO','FECHAMENTO')"
            await cur.execute(
                f"SELECT column_key, label, description, type FROM funnel_columns WHERE type = %s ORDER BY {order}",
                (type,)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


@router.put("/{column_key}",
            dependencies=[Depends(require_roles("ADMIN", "GERENTE"))])
async def update(column_key: str, data: FunnelColumnUpdate, type: str = "CRM") -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE funnel_columns SET label = %s, description = %s WHERE column_key = %s AND type = %s",
                (data.label, data.description, column_key, type),
            )
            return {"message": "Coluna atualizada com sucesso"}
