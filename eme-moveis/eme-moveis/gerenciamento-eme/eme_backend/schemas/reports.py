from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ReportFormat(str, Enum):
    JSON = "json"
    PDF = "pdf"
    XLSX = "xlsx"


# ── Filtros por área ────────────────────────────────────────────

class FinancialReportFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    type: Optional[str] = None  # ENTRADA | SAIDA
    category: Optional[str] = None
    status: Optional[str] = None  # PAGO | PENDENTE
    project_id: Optional[str] = None


class ClientsReportFilters(BaseModel):
    created_from: Optional[date] = None
    created_to: Optional[date] = None
    search: Optional[str] = None  # nome, email ou cpf/cnpj


class ProjectsReportFilters(BaseModel):
    status: Optional[str] = None
    client_id: Optional[str] = None
    deadline_from: Optional[date] = None
    deadline_to: Optional[date] = None


class StockReportFilters(BaseModel):
    report_mode: str = "items"  # "items" | "movements"
    category_id: Optional[str] = None
    low_stock_only: bool = False
    movement_type: Optional[str] = None  # ENTRADA | SAIDA (para movimentações)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


# ── Estrutura de resposta padronizada ───────────────────────────

class ReportColumn(BaseModel):
    key: str
    label: str


class ReportSummaryItem(BaseModel):
    label: str
    value: str
    tone: Optional[str] = None  # 'positive' | 'negative' | 'neutral'


class ReportResponse(BaseModel):
    title: str
    generated_at: str
    filters_applied: dict
    summary: list[ReportSummaryItem]
    columns: list[ReportColumn]
    rows: list[dict]
