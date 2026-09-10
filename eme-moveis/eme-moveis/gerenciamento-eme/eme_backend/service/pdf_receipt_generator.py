"""Geração do recibo em PDF, replicando o layout oficial da EME Móveis."""

import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from service.receipt_service import ReceiptData

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "logo_eme.png")

_PRETO = HexColor("#1a1a1a")
_CINZA = HexColor("#555555")
_CINZA_CLARO = HexColor("#888888")


def gerar_recibo_pdf(data: ReceiptData) -> bytes:
    """Gera o PDF do recibo e retorna os bytes do arquivo."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin = 20 * mm
    y = height - 25 * mm

    # ---- Logo ----
    logo_w = 26 * mm
    logo_h = 14.6 * mm
    if os.path.exists(_LOGO_PATH):
        c.drawImage(
            ImageReader(_LOGO_PATH),
            margin,
            y - logo_h + 4,
            width=logo_w,
            height=logo_h,
            mask="auto",
            preserveAspectRatio=True,
        )

    # ---- Dados da empresa (ao lado do logo) ----
    text_x = margin + logo_w + 6 * mm
    text_y = y
    c.setFont("Helvetica", 9)
    c.setFillColor(_PRETO)
    c.drawString(text_x, text_y, data.empresa_razao_social)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(_CINZA)
    text_y -= 4.5 * mm
    c.drawString(text_x, text_y, f"CNPJ/CPF: {data.empresa_cnpj}     IE: {data.empresa_ie}")

    text_y -= 4.5 * mm
    c.drawString(text_x, text_y, data.empresa_endereco)

    text_y -= 4.5 * mm
    c.drawString(text_x, text_y, f"CEP: {data.empresa_cep}")

    # ---- Linha horizontal superior ----
    line_y = y - logo_h - 2 * mm
    c.setStrokeColor(_PRETO)
    c.setLineWidth(1.1)
    c.line(margin, line_y, width - margin, line_y)

    # ---- Título "Recibo" + valor ----
    title_y = line_y - 14 * mm
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(_PRETO)
    c.drawString(margin, title_y, "Recibo")

    c.setFont("Helvetica", 11)
    c.setFillColor(_CINZA)
    valor_label = "R$"
    c.drawRightString(width - margin - 38 * mm, title_y - 1, valor_label)

    c.setFont("Helvetica", 20)
    c.setFillColor(_PRETO)
    c.drawRightString(width - margin, title_y, data.valor_formatado.replace("R$", "").strip())

    # ---- Linha pontilhada ----
    dash_y = title_y - 6 * mm
    c.setDash(2, 2)
    c.setLineWidth(0.8)
    c.setStrokeColor(_CINZA_CLARO)
    c.line(margin, dash_y, width - margin, dash_y)
    c.setDash()  # reset

    # ---- Corpo do recibo ----
    body_y = dash_y - 12 * mm
    c.setFont("Helvetica", 10.5)
    c.setFillColor(_PRETO)

    corpo_texto = (
        f"{data.acao_label} {data.pessoa_nome} a importância de {data.valor_extenso} "
        f"referente ao {data.status_label} de '{data.descricao}'."
    )

    body_y = _draw_wrapped_text(
        c, corpo_texto, margin, body_y, width - 2 * margin,
        font="Helvetica", size=10.5, leading=5.6 * mm,
    )

    body_y -= 8 * mm
    confirmacao_texto = (
        "Para confirmar a veracidade deste documento e da quantia "
        "envolvida, assino neste documento firmando o presente recibo nesta data."
    )
    body_y = _draw_wrapped_text(
        c, confirmacao_texto, margin, body_y, width - 2 * margin,
        font="Helvetica", size=10.5, leading=5.6 * mm,
    )

    # ---- Local e data ----
    body_y -= 10 * mm
    c.setFont("Helvetica", 10.5)
    c.drawCentredString(
        width / 2, body_y, f"{data.local}, {data.data_extenso}"
    )

    # ---- Assinatura ----
    sign_y = body_y - 22 * mm
    sign_width = 110 * mm
    sign_x_start = (width - sign_width) / 2
    c.setLineWidth(0.8)
    c.setStrokeColor(_PRETO)
    c.line(sign_x_start, sign_y, sign_x_start + sign_width, sign_y)

    c.setFont("Helvetica", 10)
    c.setFillColor(_PRETO)
    c.drawCentredString(width / 2, sign_y - 5.5 * mm, data.empresa_razao_social)

    c.setFont("Helvetica", 9.5)
    c.setFillColor(_CINZA)
    c.drawCentredString(width / 2, sign_y - 10.5 * mm, f"CNPJ/CPF: {data.empresa_cnpj}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def _draw_wrapped_text(c: canvas.Canvas, text: str, x: float, y: float,
                        max_width: float, font: str, size: float, leading: float) -> float:
    """Desenha texto com quebra automática de linha; retorna o y final."""
    c.setFont(font, size)
    words = text.split(" ")
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if c.stringWidth(test_line, font, size) <= max_width:
            line = test_line
        else:
            c.drawString(x, y, line)
            y -= leading
            line = word
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y
