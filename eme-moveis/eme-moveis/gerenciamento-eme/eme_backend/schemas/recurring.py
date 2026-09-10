from pydantic import BaseModel
from typing import Optional
from datetime import date as date_type
from enum import Enum


class RecurringFrequency(str, Enum):
    SEMANAL = "SEMANAL"
    QUINZENAL = "QUINZENAL"
    MENSAL = "MENSAL"
    ANUAL = "ANUAL"


class FinancialMode(str, Enum):
    NORMAL = "NORMAL"
    PARCELADO = "PARCELADO"
    FIXO = "FIXO"


class FinancialCreateExtended(BaseModel):
    """Schema estendido para criação de lançamentos com suporte a parcelas e recorrência."""
    description: str
    type: str  # ENTRADA | SAIDA
    category: str
    amount: float
    date: date_type
    project_id: Optional[str] = None
    status: str = "PENDENTE"
    # Modo de criação
    mode: FinancialMode = FinancialMode.NORMAL
    # Parcelado
    installments: Optional[int] = None  # número de parcelas (2-60)
    # Fixo/Recorrente
    frequency: Optional[RecurringFrequency] = None


class RecurringResponse(BaseModel):
    id: str
    description: str
    type: str
    category: str
    amount: float
    frequency: str
    start_date: str
    next_date: str
    project_id: Optional[str] = None
    active: bool

    class Config:
        from_attributes = True
