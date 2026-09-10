"""Geração de relatórios em PDF (resumo + tabela detalhada)."""

import io
import os

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from schemas.reports import ReportResponse

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "logo_eme.png")

_PRETO = HexColor("#1a1a1a")
_CINZA = HexColor("#555555")
_CINZA_CLARO = HexColor("#888888")
_VERMELHO = HexColor("#b91c1c")
_VERDE = HexColor("#15803d")
_HEADER_BG = HexColor("#f4f4f5")
_ROW_ALT_BG = HexColor("#fafafa")

_TONE_COLORS = {
    "positive": _VERDE,
    "negative": _VERMELHO,
    "neutral": _PRETO,
}


def gerar_relatorio_pdf(report: ReportResponse) -> bytes:
    """Gera o PDF do relatório (paisagem) e retorna os bytes do arquivo."""
    buffer = io.BytesIO()
    page_size = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    margin = 15 * mm
    y = height - 18 * mm

    # ---- Cabeçalho ----
    logo_w = 18 * mm
    logo_h = 10 * mm
    if os.path.exists(_LOGO_PATH):
        c.drawImage(
            ImageReader(_LOGO_PATH), margin, y - logo_h + 3,
            width=logo_w, height=logo_h, mask="auto", preserveAspectRatio=True,
        )

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(_PRETO)
    c.drawString(margin + logo_w + 5 * mm, y - 2, report.title)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(_CINZA)
    c.drawRightString(width - margin, y - 2, f"Gerado em {report.generated_at}")

    y -= logo_h + 4 * mm
    c.setStrokeColor(_PRETO)
    c.setLineWidth(1)
    c.line(margin, y, width - margin, y)
    y -= 8 * mm

    # ---- Resumo (cards em linha) ----
    if report.summary:
        n = len(report.summary)
        card_gap = 4 * mm
        card_w = (width - 2 * margin - card_gap * (n - 1)) / n if n else 0
        card_h = 16 * mm

        for i, item in enumerate(report.summary):
            x = margin + i * (card_w + card_gap)
            c.setStrokeColor(_CINZA_CLARO)
            c.setLineWidth(0.6)
            c.roundRect(x, y - card_h, card_w, card_h, 2, stroke=1, fill=0)

            c.setFont("Helvetica", 7)
            c.setFillColor(_CINZA)
            label = item.label if len(item.label) < 28 else item.label[:26] + "…"
            c.drawString(x + 2.5 * mm, y - 5.5 * mm, label.upper())

            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(_TONE_COLORS.get(item.tone or "neutral", _PRETO))
            value = item.value if len(item.value) < 22 else item.value[:20] + "…"
            c.drawString(x + 2.5 * mm, y - 12 * mm, value)

        y -= card_h + 8 * mm

    # ---- Tabela detalhada ----
    if report.rows:
        col_count = len(report.columns)
        usable_width = width - 2 * margin
        col_width = usable_width / col_count if col_count else usable_width

        row_h = 7 * mm
        header_h = 8 * mm

        def draw_header(yy: float) -> float:
            c.setFillColor(_HEADER_BG)
            c.rect(margin, yy - header_h, usable_width, header_h, stroke=0, fill=1)
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(_PRETO)
            for i, col in enumerate(report.columns):
                x = margin + i * col_width + 2 * mm
                c.drawString(x, yy - header_h + 2.6 * mm, col.label.upper())
            c.setStrokeColor(_CINZA_CLARO)
            c.setLineWidth(0.4)
            c.line(margin, yy - header_h, width - margin, yy - header_h)
            return yy - header_h

        y = draw_header(y)

        c.setFont("Helvetica", 7.5)
        bottom_limit = 14 * mm

        for idx, row in enumerate(report.rows):
            if y - row_h < bottom_limit:
                c.showPage()
                y = height - 15 * mm
                y = draw_header(y)
                c.setFont("Helvetica", 7.5)

            if idx % 2 == 1:
                c.setFillColor(_ROW_ALT_BG)
                c.rect(margin, y - row_h, usable_width, row_h, stroke=0, fill=1)

            c.setFillColor(_PRETO)
            for i, col in enumerate(report.columns):
                x = margin + i * col_width + 2 * mm
                raw_value = str(row.get(col.key, ""))
                max_chars = max(6, int(col_width / (1.7 * mm)))
                value = raw_value if len(raw_value) <= max_chars else raw_value[: max_chars - 1] + "…"
                c.drawString(x, y - row_h + 2.3 * mm, value)

            c.setStrokeColor(HexColor("#e5e5e5"))
            c.setLineWidth(0.3)
            c.line(margin, y - row_h, width - margin, y - row_h)

            y -= row_h
    else:
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(_CINZA)
        c.drawString(margin, y - 8 * mm, "Nenhum registro encontrado para os filtros selecionados.")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
