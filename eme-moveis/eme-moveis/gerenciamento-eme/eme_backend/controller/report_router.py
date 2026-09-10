from typing import Optional
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from endpoints.security import require_roles
from schemas.reports import (
    FinancialReportFilters,
    ClientsReportFilters,
    ProjectsReportFilters,
    StockReportFilters,
    ReportResponse,
)
from service.report_service import report_service
from service.pdf_report_generator import gerar_relatorio_pdf
from service.xlsx_report_generator import gerar_relatorio_xlsx

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
    dependencies=[Depends(require_roles("ADMIN", "GERENTE"))],
)


def _export_response(report: ReportResponse, export: Literal["pdf", "xlsx"], filename_prefix: str) -> Response:
    if export == "pdf":
        content = gerar_relatorio_pdf(report)
        media_type = "application/pdf"
        extension = "pdf"
    elif export == "xlsx":
        content = gerar_relatorio_xlsx(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de exportação inválido. Utilize 'pdf' ou 'xlsx'.",
        )

    filename = f"{filename_prefix}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Financeiro ───────────────────────────────────────────────────

@router.get("/financial", response_model=ReportResponse)
async def get_financial_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    project_id: Optional[str] = None,
) -> ReportResponse:
    filters = FinancialReportFilters(
        date_from=date_from or None,
        date_to=date_to or None,
        type=type or None,
        category=category or None,
        status=status_filter or None,
        project_id=project_id or None,
    )
    return await report_service.build_financial_report(filters)


@router.get("/financial/export")
async def export_financial_report(
    export: Literal["pdf", "xlsx"] = "pdf",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Response:
    filters = FinancialReportFilters(
        date_from=date_from or None,
        date_to=date_to or None,
        type=type or None,
        category=category or None,
        status=status_filter or None,
        project_id=project_id or None,
    )
    report = await report_service.build_financial_report(filters)
    return _export_response(report, export, "relatorio-financeiro")


# ── Clientes ─────────────────────────────────────────────────────

@router.get("/clients", response_model=ReportResponse)
async def get_clients_report(
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    search: Optional[str] = None,
) -> ReportResponse:
    filters = ClientsReportFilters(
        created_from=created_from or None,
        created_to=created_to or None,
        search=search or None,
    )
    return await report_service.build_clients_report(filters)


@router.get("/clients/export")
async def export_clients_report(
    export: Literal["pdf", "xlsx"] = "pdf",
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    search: Optional[str] = None,
) -> Response:
    filters = ClientsReportFilters(
        created_from=created_from or None,
        created_to=created_to or None,
        search=search or None,
    )
    report = await report_service.build_clients_report(filters)
    return _export_response(report, export, "relatorio-clientes")


# ── Projetos ─────────────────────────────────────────────────────

@router.get("/projects", response_model=ReportResponse)
async def get_projects_report(
    status_filter: Optional[str] = None,
    client_id: Optional[str] = None,
    deadline_from: Optional[str] = None,
    deadline_to: Optional[str] = None,
) -> ReportResponse:
    filters = ProjectsReportFilters(
        status=status_filter or None,
        client_id=client_id or None,
        deadline_from=deadline_from or None,
        deadline_to=deadline_to or None,
    )
    return await report_service.build_projects_report(filters)


@router.get("/projects/export")
async def export_projects_report(
    export: Literal["pdf", "xlsx"] = "pdf",
    status_filter: Optional[str] = None,
    client_id: Optional[str] = None,
    deadline_from: Optional[str] = None,
    deadline_to: Optional[str] = None,
) -> Response:
    filters = ProjectsReportFilters(
        status=status_filter or None,
        client_id=client_id or None,
        deadline_from=deadline_from or None,
        deadline_to=deadline_to or None,
    )
    report = await report_service.build_projects_report(filters)
    return _export_response(report, export, "relatorio-projetos")


# ── Estoque ──────────────────────────────────────────────────────

@router.get("/stock", response_model=ReportResponse)
async def get_stock_report(
    report_mode: Literal["items", "movements"] = "items",
    category_id: Optional[str] = None,
    low_stock_only: bool = False,
    movement_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> ReportResponse:
    filters = StockReportFilters(
        report_mode=report_mode,
        category_id=category_id or None,
        low_stock_only=low_stock_only,
        movement_type=movement_type or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return await report_service.build_stock_report(filters)


@router.get("/stock/export")
async def export_stock_report(
    export: Literal["pdf", "xlsx"] = "pdf",
    report_mode: Literal["items", "movements"] = "items",
    category_id: Optional[str] = None,
    low_stock_only: bool = False,
    movement_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Response:
    filters = StockReportFilters(
        report_mode=report_mode,
        category_id=category_id or None,
        low_stock_only=low_stock_only,
        movement_type=movement_type or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    report = await report_service.build_stock_report(filters)
    prefix = "relatorio-estoque-itens" if report_mode == "items" else "relatorio-estoque-movimentacoes"
    return _export_response(report, export, prefix)


@router.get("/dre")
async def get_dre(
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> dict:
    """Demonstrativo de Resultado do Exercício (DRE)."""
    return await report_service.build_dre(month=month, year=year)


@router.get("/crm")
async def get_crm_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Relatório CRM: negociações, conversão, ticket médio e fluxo de caixa consolidado."""
    return await report_service.build_crm_report(date_from=date_from, date_to=date_to)
