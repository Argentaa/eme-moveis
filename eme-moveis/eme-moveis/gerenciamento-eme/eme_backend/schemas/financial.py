from pydantic import BaseModel
from typing import Optional
from datetime import date as date_type
from enum import Enum


class FinancialType(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class FinancialStatus(str, Enum):
    PAGO = "PAGO"
    PENDENTE = "PENDENTE"


class FinancialRecordBase(BaseModel):
    description: str
    type: FinancialType
    category: str
    amount: float
    date: date_type
    due_date: date_type
    project_id: Optional[str] = None
    status: FinancialStatus


class FinancialRecordCreate(FinancialRecordBase):
    pass


class FinancialRecordUpdate(BaseModel):
    description: Optional[str] = None
    type: Optional[FinancialType] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[date_type] = None
    due_date: Optional[date_type] = None
    project_id: Optional[str] = None
    status: Optional[FinancialStatus] = None


class FinancialRecordResponse(FinancialRecordBase):
    id: str

    class Config:
        from_attributes = True
