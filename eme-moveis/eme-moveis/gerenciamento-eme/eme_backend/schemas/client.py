from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime


class FunnelStatus(str, Enum):
    PROSPECCAO = "PROSPECCAO"
    ORCAMENTO = "ORCAMENTO"
    APRESENTACAO = "APRESENTACAO"
    NEGOCIACAO = "NEGOCIACAO"
    FECHAMENTO = "FECHAMENTO"
    PERDIDO = "PERDIDO"


class ClientBase(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    cpf_cnpj: str
    address: str
    funnel_status: FunnelStatus = FunnelStatus.PROSPECCAO
    lost_reason: Optional[str] = None
    estimated_value: Optional[float] = None
    lead_source: Optional[str] = None
    lead_source: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    address: Optional[str] = None
    funnel_status: Optional[FunnelStatus] = None
    lost_reason: Optional[str] = None
    estimated_value: Optional[float] = None
    lead_source: Optional[str] = None
    lead_source: Optional[str] = None


class ClientResponse(ClientBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
