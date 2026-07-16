"""
parsing/text.py
---------------
Camada de NORMALIZAÇÃO de texto. É a base de todo o parser: transforma a fala
crua (com acentos, maiúsculas, pontuação) numa forma estável e comparável.

Princípio: o resto do parser trabalha sempre sobre texto normalizado (sem
acento, minúsculo), para que os dicionários possam ser escritos UMA vez, de
forma natural ("inseminação"), sem precisar cadastrar cada variação de
digitação/transcrição ("inseminacao", "Inseminação"...).
"""

import re
import unicodedata

# Números por extenso mais comuns na fala de campo (idade e dose costumam ser
# baixas). Usado tanto para idade ("dois anos") quanto para dose ("três ml").
NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "meio": 0.5, "meia": 0.5,
}


def remover_acentos(texto: str) -> str:
    """"coração" -> "coracao". Decompõe os caracteres acentuados e descarta os
    diacríticos, deixando apenas as letras-base ASCII."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Forma canônica para COMPARAÇÃO: minúsculo, sem acento, espaços colapsados.
    Preserva letras/números/espaços; troca o resto por espaço."""
    if not texto:
        return ""
    texto = remover_acentos(texto.lower())
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def tokenizar(texto: str) -> list:
    """Quebra o texto normalizado em palavras (apenas letras). Números ficam de
    fora de propósito — quem cuida deles são os extratores regex."""
    return re.findall(r"[a-z]+", normalizar(texto))


def numero_por_extenso(palavra: str):
    """Devolve o valor numérico de um número escrito por extenso, ou None.
    A palavra é normalizada antes ('três' e 'tres' batem no mesmo)."""
    return NUMEROS_POR_EXTENSO.get(normalizar(palavra))


# ---------------------------------------------------------------------------
# NÚMEROS COMPOSTOS POR EXTENSO -> DÍGITOS ("vinte e dois" -> "22")
# ---------------------------------------------------------------------------
# O transcritor do Android ora entrega dígitos ("vaca 22"), ora entrega por
# extenso ("vaca vinte e dois") — depende do aparelho e do ritmo da fala. Todo
# o parser (segmentação por animal, peso, brinco) trabalha com dígitos, então
# convertemos ANTES de interpretar. Sem isto, "vaca vinte e dois e vinte e
# tres" só encontrava animal nenhum ou só o primeiro.
_UNIDADES = {
    "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9,
}
_DEZ_A_DEZENOVE = {
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14,
    "catorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19,
}
_DEZENAS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
    "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
}
_CENTENAS = {
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200,
    "trezentos": 300, "trezentas": 300, "quatrocentos": 400,
    "quatrocentas": 400, "quinhentos": 500, "quinhentas": 500,
    "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800,
    "novecentos": 900, "novecentas": 900,
}
# "um/uma" fica de fora de propósito: quase sempre é artigo ("uma mastite",
# "um abscesso"), não número. Só entra como continuação ("vinte e um").
_CONTINUACAO_UM = {"um": 1, "uma": 1}


def _valor_da_palavra(token, permitir_um=False):
    for tabela in (_CENTENAS, _DEZENAS, _DEZ_A_DEZENOVE, _UNIDADES):
        if token in tabela:
            return tabela[token]
    if permitir_um and token in _CONTINUACAO_UM:
        return _CONTINUACAO_UM[token]
    return None


def converter_numeros_compostos(texto: str) -> str:
    """Reescreve números por extenso como dígitos, no texto JÁ normalizado.

    Compõe centena+dezena+unidade ligadas por "e", fechando o número quando a
    próxima parcela não é menor que a anterior — assim "vinte e dois e vinte e
    tres" vira "22 e 23" (o segundo "e" liga DOIS números, não um só) e
    "trezentos e trezentos e vinte" vira "300 e 320".
    """
    tokens = texto.split()
    saida = []
    i = 0
    while i < len(tokens):
        valor = _valor_da_palavra(tokens[i])
        if valor is None:
            saida.append(tokens[i])
            i += 1
            continue
        total, menor_parcela = valor, valor
        i += 1
        while (i + 1 < len(tokens) and tokens[i] == "e"):
            proxima = _valor_da_palavra(tokens[i + 1], permitir_um=True)
            if proxima is None or proxima >= menor_parcela:
                break
            total += proxima
            menor_parcela = proxima
            i += 2
        saida.append(str(total))
    return " ".join(saida)


def normalizar_com_numeros(texto: str) -> str:
    """normalizar() + números por extenso convertidos em dígitos."""
    return converter_numeros_compostos(normalizar(texto))
