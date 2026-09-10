"""
Conversão de valores monetários para extenso em português (pt-BR).

Implementação própria, sem dependências externas, para evitar
acoplar o projeto a bibliotecas adicionais (ex.: num2words) que
podem não estar disponíveis em todos os ambientes de instalação.
"""

_UNIDADES = [
    "", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove",
]
_DEZ_A_DEZENOVE = [
    "dez", "onze", "doze", "treze", "quatorze", "quinze",
    "dezesseis", "dezessete", "dezoito", "dezenove",
]
_DEZENAS = [
    "", "", "vinte", "trinta", "quarenta", "cinquenta",
    "sessenta", "setenta", "oitenta", "noventa",
]
_CENTENAS = [
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
    "seiscentos", "setecentos", "oitocentos", "novecentos",
]

# (divisor, singular, plural)
_ESCALAS = [
    (10**9, "bilhão", "bilhões"),
    (10**6, "milhão", "milhões"),
    (10**3, "mil", "mil"),
]


def _grupo_centena(n: int) -> str:
    """Converte um número de 0 a 999 para extenso."""
    if n == 0:
        return ""
    if n == 100:
        return "cem"

    centena, resto = divmod(n, 100)
    partes = []

    if centena:
        partes.append(_CENTENAS[centena])

    if resto:
        if centena:
            partes.append("e")
        if resto < 10:
            partes.append(_UNIDADES[resto])
        elif resto < 20:
            partes.append(_DEZ_A_DEZENOVE[resto - 10])
        else:
            dezena, unidade = divmod(resto, 10)
            if unidade:
                partes.append(f"{_DEZENAS[dezena]} e {_UNIDADES[unidade]}")
            else:
                partes.append(_DEZENAS[dezena])

    return " ".join(partes)


def _inteiro_por_extenso(n: int) -> str:
    """Converte um número inteiro não negativo para extenso em pt-BR."""
    if n == 0:
        return "zero"

    grupos: list[str] = []
    restante = n

    for divisor, singular, plural in _ESCALAS:
        quantidade, restante = divmod(restante, divisor)
        if quantidade:
            if divisor == 1000 and quantidade == 1:
                grupos.append("mil")
            else:
                texto_grupo = _grupo_centena(quantidade)
                escala = plural if quantidade != 1 else singular
                grupos.append(f"{texto_grupo} {escala}")

    if restante:
        grupos.append(_grupo_centena(restante))

    if len(grupos) == 1:
        return grupos[0]

    # Regra de concordância pt-BR: usa "e" antes do último grupo quando ele
    # é menor que 100 (ou é múltiplo de cem), e vírgula entre os demais.
    ultimo_valor = restante if restante else 0
    usa_e = ultimo_valor == 0 or ultimo_valor < 100 or ultimo_valor % 100 == 0

    if usa_e:
        return ", ".join(grupos[:-1]) + " e " + grupos[-1]
    return ", ".join(grupos)


def valor_em_extenso_reais(valor: float) -> str:
    """
    Converte um valor monetário (float, em reais) para texto por extenso,
    no formato usado em recibos: "Trinta e Cinco mil Reais" ou
    "Mil Duzentos e Trinta Reais e Cinquenta Centavos".
    """
    valor_arredondado = round(valor, 2)
    inteiro = int(valor_arredondado)
    centavos = round((valor_arredondado - inteiro) * 100)

    # Corrige possíveis erros de arredondamento (ex.: 99.999999 -> 100 centavos)
    if centavos == 100:
        inteiro += 1
        centavos = 0

    texto_inteiro = _inteiro_por_extenso(inteiro)
    sufixo_reais = "Real" if inteiro == 1 else "Reais"

    # "um milhão de Reais", "dois milhões de Reais"... mas não quando há
    # resto (ex.: 1.234.567 -> "Um milhão, duzentos... Reais", sem "de")
    usa_de = inteiro >= 10**6 and inteiro % 10**6 == 0

    conector = " de " if usa_de else " "
    resultado = f"{texto_inteiro.capitalize()}{conector}{sufixo_reais}"

    if centavos:
        texto_centavos = _inteiro_por_extenso(centavos)
        sufixo_centavos = "Centavo" if centavos == 1 else "Centavos"
        resultado += f" e {texto_centavos} {sufixo_centavos}"

    return resultado
