from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status

from repo.financial_repo import financial_repo
from repo.project_repo import project_repo
from repo.client_repo import client_repo
from service.number_to_words import valor_em_extenso_reais

# Dados fixos da empresa emitente (EME Móveis).
# Mantidos em código por serem dados institucionais estáveis;
# podem futuramente migrar para variáveis de ambiente/config se necessário.
EMPRESA = {
    "razao_social": "INDUSTRIA DE MOVEIS EME LTDA",
    "cnpj": "38.229.090/0001-60",
    "ie": "0490065724",
    "endereco": "BR 386 KM 32 - Rua Lateral, 02, Frederico Westphalen - RS",
    "cep": "98400-000",
    "cidade": "Frederico Westphalen",
    "uf": "RS",
}

_MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def _data_extenso(d: date) -> str:
    return f"{d.day:02d} de {_MESES_PT[d.month]} de {d.year}"


@dataclass
class ReceiptData:
    """Estrutura com todos os campos necessários para montar o recibo."""

    empresa_razao_social: str
    empresa_cnpj: str
    empresa_ie: str
    empresa_endereco: str
    empresa_cep: str

    valor_numerico: float
    valor_formatado: str
    valor_extenso: str

    pessoa_nome: str
    acao_label: str  # "Recebi de" ou "Pagamos a"
    descricao: str
    status_label: str  # "pagamento integral" / "pagamento parcial" etc.

    local: str
    data_extenso: str

    record_id: str
    record_type: str  # ENTRADA | SAIDA
    record_status: str  # PAGO | PENDENTE


class ReceiptService:
    """Monta os dados de um recibo a partir de um lançamento financeiro."""

    async def build_receipt_data(self, record_id: str) -> ReceiptData:
        record = await financial_repo.find_by_id(record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro financeiro não encontrado",
            )

        pessoa_nome = "Cliente não identificado"
        if record.get("project_id"):
            project = await project_repo.find_by_id(record["project_id"])
            if project and project.get("client_id"):
                client = await client_repo.find_by_id(project["client_id"])
                if client:
                    pessoa_nome = client["name"]
                elif project.get("client_name"):
                    pessoa_nome = project["client_name"]

        record_type = record["type"]
        record_status = record["status"]
        amount = float(record["amount"])

        if record_type == "ENTRADA":
            acao_label = "Recebi de"
            status_label = "pagamento integral" if record_status == "PAGO" else "pagamento (em aberto)"
        else:
            acao_label = "Pagamos a"
            status_label = "pagamento integral" if record_status == "PAGO" else "pagamento (em aberto)"

        valor_formatado = f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        record_date = record["date"]
        if isinstance(record_date, str):
            record_date = date.fromisoformat(record_date)

        return ReceiptData(
            empresa_razao_social=EMPRESA["razao_social"],
            empresa_cnpj=EMPRESA["cnpj"],
            empresa_ie=EMPRESA["ie"],
            empresa_endereco=EMPRESA["endereco"],
            empresa_cep=EMPRESA["cep"],
            valor_numerico=amount,
            valor_formatado=valor_formatado,
            valor_extenso=valor_em_extenso_reais(amount),
            pessoa_nome=pessoa_nome,
            acao_label=acao_label,
            descricao=record["description"],
            status_label=status_label,
            local=f"{EMPRESA['cidade']} ({EMPRESA['uf']})",
            data_extenso=_data_extenso(record_date),
            record_id=record["id"],
            record_type=record_type,
            record_status=record_status,
        )


receipt_service = ReceiptService()
