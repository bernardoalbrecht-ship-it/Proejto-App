"""
nlp/text.py
-----------
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
