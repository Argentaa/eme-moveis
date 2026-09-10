from typing import Optional
from fastapi import HTTPException, status
from repo.calendar_repo import calendar_repo
from schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    NotificationResponse,
)


class CalendarService:

    # ── Eventos ─────────────────────────────────────────────

    async def get_all(self, month: Optional[int] = None, year: Optional[int] = None) -> list[CalendarEventResponse]:
        rows = await calendar_repo.find_all(month=month, year=year)
        return [CalendarEventResponse(**self._serialize(r)) for r in rows]

    async def get_today(self) -> list[CalendarEventResponse]:
        rows = await calendar_repo.find_today()
        return [CalendarEventResponse(**self._serialize(r)) for r in rows]

    async def get_week(self) -> list[CalendarEventResponse]:
        rows = await calendar_repo.find_week()
        return [CalendarEventResponse(**self._serialize(r)) for r in rows]

    async def create(self, data: CalendarEventCreate) -> CalendarEventResponse:
        payload = data.model_dump()
        for key in ("start_date", "end_date"):
            if payload.get(key):
                payload[key] = str(payload[key])
        for key in ("type", "status"):
            if payload.get(key):
                val = payload[key]
                payload[key] = val.value if hasattr(val, "value") else val
        row = await calendar_repo.create(payload)
        return CalendarEventResponse(**self._serialize(row))

    async def update(self, event_id: str, data: CalendarEventUpdate) -> CalendarEventResponse:
        existing = await calendar_repo.find_by_id(event_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
        update_data = data.model_dump(exclude_unset=True)
        for key in ("type", "status"):
            if key in update_data and update_data[key] is not None:
                val = update_data[key]
                update_data[key] = val.value if hasattr(val, "value") else val
        for key in ("start_date", "end_date"):
            if key in update_data and update_data[key] is not None:
                update_data[key] = str(update_data[key])
        row = await calendar_repo.update(event_id, update_data)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao atualizar evento")
        return CalendarEventResponse(**self._serialize(row))

    async def delete(self, event_id: str) -> dict:
        deleted = await calendar_repo.delete(event_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
        return {"message": "Evento removido com sucesso"}

    # ── Notificações ─────────────────────────────────────────

    async def get_notifications(self, user_id: Optional[str] = None, unread_only: bool = False) -> list[NotificationResponse]:
        rows = await calendar_repo.find_notifications(user_id=user_id, unread_only=unread_only)
        return [NotificationResponse(**r) for r in rows]

    async def count_unread(self, user_id: Optional[str] = None) -> dict:
        count = await calendar_repo.count_unread(user_id=user_id)
        return {"unread": count}

    async def mark_read(self, notif_id: str) -> dict:
        updated = await calendar_repo.mark_read(notif_id)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificação não encontrada")
        return {"message": "Notificação marcada como lida"}

    async def mark_all_read(self, user_id: Optional[str] = None) -> dict:
        count = await calendar_repo.mark_all_read(user_id=user_id)
        return {"message": f"{count} notificação(ões) marcada(s) como lida(s)"}

    async def generate_deadline_alerts(self) -> dict:
        """Gera notificações automáticas para projetos próximos do prazo ou atrasados."""
        projects = await calendar_repo.find_projects_with_deadline_alert()
        created = 0
        for proj in projects:
            days = proj.get("days_remaining", 0)
            if days < 0:
                title = f"Projeto atrasado: {proj['title']}"
                message = f"O projeto '{proj['title']}' do cliente {proj.get('client_name', 'N/A')} está {abs(days)} dia(s) atrasado."
                notif_type = "PROJETO_ATRASADO"
            elif days == 1:
                title = f"Entrega amanhã: {proj['title']}"
                message = f"O projeto '{proj['title']}' do cliente {proj.get('client_name', 'N/A')} tem entrega amanhã."
                notif_type = "PRAZO_PROJETO"
            elif days <= 3:
                title = f"Prazo em {days} dias: {proj['title']}"
                message = f"O projeto '{proj['title']}' do cliente {proj.get('client_name', 'N/A')} vence em {days} dia(s)."
                notif_type = "PRAZO_PROJETO"
            elif days <= 7:
                title = f"Atenção: prazo em {days} dias"
                message = f"O projeto '{proj['title']}' do cliente {proj.get('client_name', 'N/A')} vence em {days} dia(s)."
                notif_type = "PRAZO_PROJETO"
            else:
                continue
            await calendar_repo.create_notification(
                title=title,
                message=message,
                notif_type=notif_type,
                project_id=proj["id"],
            )
            created += 1
        return {"generated": created}

    # ── Helpers ──────────────────────────────────────────────

    def _serialize(self, row: dict) -> dict:
        """Converte campos de data/hora do MySQL para string, compatível com Pydantic.
        MySQL retorna TIME como timedelta, DATE como date e DATETIME como datetime."""
        from datetime import date, time, datetime, timedelta
        result = dict(row)
        for key, val in result.items():
            if isinstance(val, timedelta):
                # TIME vem como timedelta: converte para "HH:MM:SS"
                total_seconds = int(val.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                result[key] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            elif isinstance(val, datetime):
                result[key] = val
            elif isinstance(val, date):
                result[key] = str(val)
        return result


calendar_service = CalendarService()
