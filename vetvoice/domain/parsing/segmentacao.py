"""
parsing/segmentacao.py
----------------------
Divide a fala de uma RONDA (vários animais numa gravação só) em trechos por
animal. Cada vez que o veterinário diz "vaca <número>" (ou brinco/animal/
número), começa um novo trecho atribuído àquele número. Trechos seguidos do
MESMO número são unidos (o veterinário voltou a falar do mesmo animal).

É DADO/REGEX puro, sem estado — fácil de testar (tests/test_segmentacao.py).
"""

import re

# "vaca 12", "brinco 340", "animal 7", "número 22"... (número em dígitos)
_MARCADOR = re.compile(
    r"\b(?:vacas?|vaquinha|brincos?|animal|animais|n[uú]meros?|n)\s+(\d{1,6})\b",
    re.IGNORECASE)


def segmentar_por_animal(texto):
    """[(id_vaca, trecho), ...] na ordem em que os animais foram ditados.
    Lista vazia se nenhum número de animal for encontrado."""
    texto = (texto or "").strip()
    if not texto:
        return []
    marcas = list(_MARCADOR.finditer(texto))
    if not marcas:
        return []

    bruto = []
    for i, marca in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        id_vaca = marca.group(1)
        trecho = texto[marca.start():fim].strip()
        bruto.append((id_vaca, trecho))

    # Une trechos consecutivos do mesmo animal.
    unido = []
    for id_vaca, trecho in bruto:
        if unido and unido[-1][0] == id_vaca:
            unido[-1] = (id_vaca, (unido[-1][1] + " " + trecho).strip())
        else:
            unido.append((id_vaca, trecho))
    return unido
