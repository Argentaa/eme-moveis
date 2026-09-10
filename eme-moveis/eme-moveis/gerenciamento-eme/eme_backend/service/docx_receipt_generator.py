"""Geração do recibo em DOCX (Word), replicando o layout oficial da EME Móveis."""

import io
import os

from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from service.receipt_service import ReceiptData

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "logo_eme.png")

_PRETO = RGBColor(0x1A, 0x1A, 0x1A)
_CINZA = RGBColor(0x55, 0x55, 0x55)


def _set_cell_borders(cell, **kwargs):
    """Define bordas individuais de uma célula (top/bottom/left/right)."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)

    for edge, spec in kwargs.items():
        tag = f"w:{edge}"
        element = tcBorders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            tcBorders.append(element)
        element.set(qn("w:val"), spec.get("val", "single"))
        element.set(qn("w:sz"), str(spec.get("sz", 6)))
        element.set(qn("w:color"), spec.get("color", "1A1A1A"))


def _add_horizontal_rule(paragraph, color="1A1A1A", size=12):
    """Adiciona uma borda inferior ao parágrafo, simulando uma linha horizontal."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_dashed_rule(paragraph, color="888888", size=6):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "dashed")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def gerar_recibo_docx(data: ReceiptData) -> bytes:
    """Gera o documento Word (.docx) do recibo e retorna os bytes do arquivo."""
    doc = Document()

    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(20)
    section.right_margin = Mm(20)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    style.font.color.rgb = _PRETO

    # ---- Cabeçalho: logo + dados da empresa em tabela (2 colunas) ----
    header_table = doc.add_table(rows=1, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    header_table.autofit = False
    header_table.columns[0].width = Mm(32)
    header_table.columns[1].width = Mm(138)

    logo_cell = header_table.rows[0].cells[0]
    logo_cell.width = Mm(32)
    if os.path.exists(_LOGO_PATH):
        logo_paragraph = logo_cell.paragraphs[0]
        run = logo_paragraph.add_run()
        run.add_picture(_LOGO_PATH, width=Mm(28))

    info_cell = header_table.rows[0].cells[1]
    info_cell.width = Mm(138)

    p = info_cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(data.empresa_razao_social)
    run.font.size = Pt(10)
    run.font.color.rgb = _PRETO
    run.bold = False

    linhas_info = [
        f"CNPJ/CPF: {data.empresa_cnpj}     IE: {data.empresa_ie}",
        data.empresa_endereco,
        f"CEP: {data.empresa_cep}",
    ]
    for linha in linhas_info:
        p2 = info_cell.add_paragraph()
        p2.paragraph_format.space_after = Pt(2)
        r2 = p2.add_run(linha)
        r2.font.size = Pt(9)
        r2.font.color.rgb = _CINZA

    for row in header_table.rows:
        for cell in row.cells:
            _set_cell_borders(
                cell,
                top={"val": "nil"}, bottom={"val": "nil"},
                left={"val": "nil"}, right={"val": "nil"},
            )

    # ---- Linha horizontal ----
    rule_p = doc.add_paragraph()
    rule_p.paragraph_format.space_before = Pt(8)
    rule_p.paragraph_format.space_after = Pt(10)
    _add_horizontal_rule(rule_p)

    # ---- Título "Recibo" + valor (tabela 2 colunas, sem bordas) ----
    title_table = doc.add_table(rows=1, cols=2)
    title_table.autofit = False
    title_table.columns[0].width = Mm(85)
    title_table.columns[1].width = Mm(85)

    title_cell = title_table.rows[0].cells[0]
    title_p = title_cell.paragraphs[0]
    title_run = title_p.add_run("Recibo")
    title_run.bold = True
    title_run.font.size = Pt(24)
    title_run.font.color.rgb = _PRETO

    value_cell = title_table.rows[0].cells[1]
    value_p = value_cell.paragraphs[0]
    value_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    value_run = value_p.add_run(data.valor_formatado)
    value_run.font.size = Pt(18)
    value_run.font.color.rgb = _PRETO

    for row in title_table.rows:
        for cell in row.cells:
            _set_cell_borders(
                cell,
                top={"val": "nil"}, bottom={"val": "nil"},
                left={"val": "nil"}, right={"val": "nil"},
            )

    # ---- Linha pontilhada ----
    dash_p = doc.add_paragraph()
    dash_p.paragraph_format.space_before = Pt(6)
    dash_p.paragraph_format.space_after = Pt(16)
    _add_dashed_rule(dash_p)

    # ---- Corpo do recibo ----
    corpo_texto = (
        f"{data.acao_label} {data.pessoa_nome} a importância de {data.valor_extenso} "
        f"referente ao {data.status_label} de '{data.descricao}'."
    )
    body_p = doc.add_paragraph()
    body_p.paragraph_format.space_after = Pt(14)
    body_p.paragraph_format.line_spacing = 1.3
    body_run = body_p.add_run(corpo_texto)
    body_run.font.size = Pt(10.5)
    body_run.font.color.rgb = _PRETO

    confirmacao_texto = (
        "Para confirmar a veracidade deste documento e da quantia envolvida, "
        "assino neste documento firmando o presente recibo nesta data."
    )
    conf_p = doc.add_paragraph()
    conf_p.paragraph_format.space_after = Pt(28)
    conf_p.paragraph_format.line_spacing = 1.3
    conf_run = conf_p.add_run(confirmacao_texto)
    conf_run.font.size = Pt(10.5)
    conf_run.font.color.rgb = _PRETO

    # ---- Local e data ----
    local_p = doc.add_paragraph()
    local_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    local_p.paragraph_format.space_after = Pt(40)
    local_run = local_p.add_run(f"{data.local}, {data.data_extenso}")
    local_run.font.size = Pt(10.5)
    local_run.font.color.rgb = _PRETO

    # ---- Assinatura ----
    sign_line_p = doc.add_paragraph()
    sign_line_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sign_line_p.paragraph_format.space_after = Pt(4)
    sign_run = sign_line_p.add_run("_" * 55)
    sign_run.font.size = Pt(10.5)
    sign_run.font.color.rgb = _PRETO

    sign_name_p = doc.add_paragraph()
    sign_name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sign_name_p.paragraph_format.space_after = Pt(2)
    sign_name_run = sign_name_p.add_run(data.empresa_razao_social)
    sign_name_run.font.size = Pt(10)
    sign_name_run.font.color.rgb = _PRETO

    sign_doc_p = doc.add_paragraph()
    sign_doc_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sign_doc_run = sign_doc_p.add_run(f"CNPJ/CPF: {data.empresa_cnpj}")
    sign_doc_run.font.size = Pt(9.5)
    sign_doc_run.font.color.rgb = _CINZA

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()
