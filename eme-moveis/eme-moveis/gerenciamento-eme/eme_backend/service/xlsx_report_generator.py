"""Geração de relatórios em Excel (.xlsx) — tabela detalhada formatada."""

import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from schemas.reports import ReportResponse

_HEADER_FILL = PatternFill("solid", start_color="1A1A1A", end_color="1A1A1A")
_HEADER_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
_TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1A1A1A")
_SUBTITLE_FONT = Font(name="Calibri", size=9, italic=True, color="555555")
_BODY_FONT = Font(name="Calibri", size=10, color="1A1A1A")
_ALT_FILL = PatternFill("solid", start_color="FAFAFA", end_color="FAFAFA")
_THIN_BORDER = Border(bottom=Side(style="thin", color="E5E5E5"))


def gerar_relatorio_xlsx(report: ReportResponse) -> bytes:
    """Gera o arquivo Excel (.xlsx) do relatório com a tabela detalhada."""
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Relatório"

    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(report.columns), 1))
    sheet.cell(row=1, column=1, value=report.title).font = _TITLE_FONT

    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(len(report.columns), 1))
    sheet.cell(row=2, column=1, value=f"Gerado em {report.generated_at} — EME Móveis").font = _SUBTITLE_FONT

    header_row = 4
    for col_idx, column in enumerate(report.columns, start=1):
        cell = sheet.cell(row=header_row, column=col_idx, value=column.label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="left", vertical="center")

    for row_offset, row_data in enumerate(report.rows):
        row_idx = header_row + 1 + row_offset
        for col_idx, column in enumerate(report.columns, start=1):
            cell = sheet.cell(row=row_idx, column=col_idx, value=row_data.get(column.key, ""))
            cell.font = _BODY_FONT
            cell.border = _THIN_BORDER
            if row_offset % 2 == 1:
                cell.fill = _ALT_FILL

    # Auto-ajuste simples de largura de coluna, baseado no conteúdo
    for col_idx, column in enumerate(report.columns, start=1):
        max_len = len(column.label)
        for row_data in report.rows:
            value_len = len(str(row_data.get(column.key, "")))
            max_len = max(max_len, value_len)
        sheet.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 50)

    sheet.freeze_panes = sheet.cell(row=header_row + 1, column=1)

    if not report.rows:
        empty_row = header_row + 1
        sheet.merge_cells(start_row=empty_row, start_column=1, end_row=empty_row, end_column=max(len(report.columns), 1))
        cell = sheet.cell(row=empty_row, column=1, value="Nenhum registro encontrado para os filtros selecionados.")
        cell.font = Font(name="Calibri", size=10, italic=True, color="888888")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
