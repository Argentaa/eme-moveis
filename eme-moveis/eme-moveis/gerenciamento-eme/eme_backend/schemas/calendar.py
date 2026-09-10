from pydantic import BaseModel
from typing import Optional
from datetime import date as date_type, time, datetime
from enum import Enum


class EventType(str, Enum):
    MEDICAO = "MEDICAO"
    REUNIAO_CLIENTE = "REUNIAO_CLIENTE"
    APROVACAO_PROJETO = "APROVACAO_PROJETO"
    PRODUCAO = "PRODUCAO"
    MONTAGEM = "MONTAGEM"
    ENTREGA = "ENTREGA"
    ASSISTENCIA_TECNICA = "ASSISTENCIA_TECNICA"
    PERSONALIZADO = "PERSONALIZADO"


class EventStatus(str, Enum):
    AGENDADO = "AGENDADO"
    CONFIRMADO = "CONFIRMADO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: EventType = EventType.PERSONALIZADO
    status: EventStatus = EventStatus.AGENDADO
    start_date: date_type
    start_time: Optional[str] = None
    end_date: Optional[date_type] = None
    end_time: Optional[str] = None
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    assigned_user_id: Optional[str] = None
    observations: Optional[str] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[EventType] = None
    status: Optional[EventStatus] = None
    start_date: Optional[date_type] = None
    start_time: Optional[str] = None
    end_date: Optional[date_type] = None
    end_time: Optional[str] = None
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    assigned_user_id: Optional[str] = None
    observations: Optional[str] = None


class CalendarEventResponse(CalendarEventCreate):
    id: str
    client_name: Optional[str] = None
    project_title: Optional[str] = None
    assigned_user_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationType(str, Enum):
    PRAZO_PROJETO = "PRAZO_PROJETO"
    EVENTO_HOJE = "EVENTO_HOJE"
    EVENTO_AMANHA = "EVENTO_AMANHA"
    PROJETO_ATRASADO = "PROJETO_ATRASADO"
    ESTOQUE_BAIXO = "ESTOQUE_BAIXO"
    GERAL = "GERAL"


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: NotificationType
    read_at: Optional[datetime] = None
    event_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
