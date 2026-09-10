from typing import Optional
from fastapi import APIRouter, Depends
from endpoints.security import get_current_user, require_roles
from schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    NotificationResponse,
)
from schemas.user import TokenData
from service.calendar_service import calendar_service

router = APIRouter(
    prefix="/api/calendar",
    tags=["Calendar"],
    dependencies=[Depends(get_current_user)],
)

# ── Eventos ─────────────────────────────────────────────────

@router.get("", response_model=list[CalendarEventResponse])
async def get_all(month: Optional[int] = None, year: Optional[int] = None) -> list[CalendarEventResponse]:
    return await calendar_service.get_all(month=month, year=year)

@router.get("/today", response_model=list[CalendarEventResponse])
async def get_today() -> list[CalendarEventResponse]:
    return await calendar_service.get_today()

@router.get("/week", response_model=list[CalendarEventResponse])
async def get_week() -> list[CalendarEventResponse]:
    return await calendar_service.get_week()

@router.post("", response_model=CalendarEventResponse, status_code=201,
             dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))])
async def create(data: CalendarEventCreate) -> CalendarEventResponse:
    return await calendar_service.create(data)

@router.put("/{event_id}", response_model=CalendarEventResponse,
            dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))])
async def update(event_id: str, data: CalendarEventUpdate) -> CalendarEventResponse:
    return await calendar_service.update(event_id, data)

@router.delete("/{event_id}",
               dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))])
async def delete(event_id: str) -> dict:
    return await calendar_service.delete(event_id)

# ── Notificações ─────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: TokenData = Depends(get_current_user),
) -> list[NotificationResponse]:
    return await calendar_service.get_notifications(
        user_id=current_user.user_id,
        unread_only=unread_only,
    )

@router.get("/notifications/count")
async def count_unread(
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    return await calendar_service.count_unread(user_id=current_user.user_id)

@router.put("/notifications/{notif_id}/read")
async def mark_read(notif_id: str) -> dict:
    return await calendar_service.mark_read(notif_id)

@router.put("/notifications/read-all")
async def mark_all_read(
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    return await calendar_service.mark_all_read(user_id=current_user.user_id)

@router.post("/notifications/generate-alerts",
             dependencies=[Depends(require_roles("ADMIN", "GERENTE", "PROJETISTA"))])
async def generate_alerts() -> dict:
    return await calendar_service.generate_deadline_alerts()
