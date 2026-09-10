import uuid
from typing import Optional
from datetime import date, timedelta
import aiomysql
from repo.connection import get_pool


class CalendarRepo:

    # ── Eventos ─────────────────────────────────────────────

    async def find_all(self, month: Optional[int] = None, year: Optional[int] = None) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if month and year:
                    await cur.execute(
                        """SELECT e.*,
                                  c.name AS client_name,
                                  p.title AS project_title,
                                  u.name AS assigned_user_name
                           FROM calendar_events e
                           LEFT JOIN clients c ON e.client_id = c.id
                           LEFT JOIN projects p ON e.project_id = p.id
                           LEFT JOIN users u ON e.assigned_user_id = u.id
                           WHERE MONTH(e.start_date) = %s AND YEAR(e.start_date) = %s
                           ORDER BY e.start_date, e.start_time""",
                        (month, year),
                    )
                else:
                    await cur.execute(
                        """SELECT e.*,
                                  c.name AS client_name,
                                  p.title AS project_title,
                                  u.name AS assigned_user_name
                           FROM calendar_events e
                           LEFT JOIN clients c ON e.client_id = c.id
                           LEFT JOIN projects p ON e.project_id = p.id
                           LEFT JOIN users u ON e.assigned_user_id = u.id
                           ORDER BY e.start_date, e.start_time"""
                    )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_by_id(self, event_id: str) -> Optional[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT e.*,
                              c.name AS client_name,
                              p.title AS project_title,
                              u.name AS assigned_user_name
                       FROM calendar_events e
                       LEFT JOIN clients c ON e.client_id = c.id
                       LEFT JOIN projects p ON e.project_id = p.id
                       LEFT JOIN users u ON e.assigned_user_id = u.id
                       WHERE e.id = %s""",
                    (event_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None

    async def find_today(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT e.*,
                              c.name AS client_name,
                              p.title AS project_title,
                              u.name AS assigned_user_name
                       FROM calendar_events e
                       LEFT JOIN clients c ON e.client_id = c.id
                       LEFT JOIN projects p ON e.project_id = p.id
                       LEFT JOIN users u ON e.assigned_user_id = u.id
                       WHERE e.start_date = CURDATE()
                         AND e.status NOT IN ('CONCLUIDO', 'CANCELADO')
                       ORDER BY e.start_time"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def find_week(self) -> list[dict]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT e.*,
                              c.name AS client_name,
                              p.title AS project_title,
                              u.name AS assigned_user_name
                       FROM calendar_events e
                       LEFT JOIN clients c ON e.client_id = c.id
                       LEFT JOIN projects p ON e.project_id = p.id
                       LEFT JOIN users u ON e.assigned_user_id = u.id
                       WHERE e.start_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                         AND e.status NOT IN ('CONCLUIDO', 'CANCELADO')
                       ORDER BY e.start_date, e.start_time"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def create(self, data: dict) -> dict:
        event_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """INSERT INTO calendar_events
                       (id, title, description, type, status, start_date, start_time,
                        end_date, end_time, project_id, client_id, assigned_user_id, observations)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        event_id,
                        data["title"],
                        data.get("description"),
                        data.get("type", "PERSONALIZADO"),
                        data.get("status", "AGENDADO"),
                        data["start_date"],
                        data.get("start_time"),
                        data.get("end_date"),
                        data.get("end_time"),
                        data.get("project_id"),
                        data.get("client_id"),
                        data.get("assigned_user_id"),
                        data.get("observations"),
                    ),
                )
        return await self.find_by_id(event_id) or {}

    async def update(self, event_id: str, data: dict) -> Optional[dict]:
        allowed = {
            "title", "description", "type", "status", "start_date", "start_time",
            "end_date", "end_time", "project_id", "client_id", "assigned_user_id", "observations"
        }
        safe = {k: v for k, v in data.items() if k in allowed}
        if not safe:
            return await self.find_by_id(event_id)
        set_clauses = [f"`{k}` = %s" for k in safe]
        values = list(safe.values()) + [event_id]
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"UPDATE calendar_events SET {', '.join(set_clauses)} WHERE id = %s",
                    tuple(values),
                )
        return await self.find_by_id(event_id)

    async def delete(self, event_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM calendar_events WHERE id = %s", (event_id,))
                return cur.rowcount > 0

    # ── Notificações ─────────────────────────────────────────

    async def find_notifications(self, user_id: Optional[str] = None, unread_only: bool = False) -> list[dict]:
        pool = await get_pool()
        conditions = []
        params = []
        if user_id:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            params.append(user_id)
        if unread_only:
            conditions.append("read_at IS NULL")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    f"SELECT * FROM notifications {where} ORDER BY created_at DESC LIMIT 50",
                    tuple(params),
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def create_notification(self, title: str, message: str, notif_type: str,
                                   user_id: Optional[str] = None, event_id: Optional[str] = None,
                                   project_id: Optional[str] = None) -> dict:
        notif_id = str(uuid.uuid4())
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO notifications (id, title, message, type, user_id, event_id, project_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (notif_id, title, message, notif_type, user_id, event_id, project_id),
                )
        return {"id": notif_id, "title": title, "message": message}

    async def mark_read(self, notif_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE notifications SET read_at = NOW() WHERE id = %s",
                    (notif_id,),
                )
                return cur.rowcount > 0

    async def mark_all_read(self, user_id: Optional[str] = None) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                if user_id:
                    await cur.execute(
                        "UPDATE notifications SET read_at = NOW() WHERE read_at IS NULL AND (user_id = %s OR user_id IS NULL)",
                        (user_id,),
                    )
                else:
                    await cur.execute("UPDATE notifications SET read_at = NOW() WHERE read_at IS NULL")
                return cur.rowcount

    async def count_unread(self, user_id: Optional[str] = None) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                if user_id:
                    await cur.execute(
                        "SELECT COUNT(*) FROM notifications WHERE read_at IS NULL AND (user_id = %s OR user_id IS NULL)",
                        (user_id,),
                    )
                else:
                    await cur.execute("SELECT COUNT(*) FROM notifications WHERE read_at IS NULL")
                row = await cur.fetchone()
                return row[0] if row else 0

    async def find_projects_with_deadline_alert(self) -> list[dict]:
        """Projetos não concluídos com prazo nos próximos 7 dias ou já vencidos."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT p.*, c.name AS client_name,
                              DATEDIFF(p.deadline, CURDATE()) AS days_remaining
                       FROM projects p
                       LEFT JOIN clients c ON p.client_id = c.id
                       WHERE p.status != 'CONCLUIDO'
                         AND p.deadline <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                       ORDER BY p.deadline ASC"""
                )
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


calendar_repo = CalendarRepo()
