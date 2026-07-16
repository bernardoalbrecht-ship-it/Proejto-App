"""
parsing/segmentacao.py
----------------------
Divide a fala de uma RONDA (vários animais numa gravação só) em trechos por
animal. Cada vez que o veterinário diz "vaca <número>" (ou brinco/animal/
número), começa um novo trecho atribuído àquele número. Trechos seguidos do
MESMO número são unidos (o veterinário voltou a falar do mesmo animal).

Também entende GRUPO: "vaca 22 e 23 estão prenhas" cria um trecho para CADA
animal do grupo, com os mesmos dados. Se a fala traz uma lista de pesos do
mesmo tamanho do grupo ("pesando 300 e 320 quilos"), cada animal recebe o seu
peso, na ordem em que foram ditos.

É DADO/REGEX puro, sem estado — fácil de testar (tests/test_segmentacao.py).
"""

import re

from vetvoice.domain.parsing.text import normalizar_com_numeros

# "vaca 12", "brinco 340", "animal 7", "número 22"... (número em dígitos).
# O texto passa por normalizar_com_numeros() antes, então "vaca vinte e dois"
# já chega aqui como "vaca 22".
_MARCADOR = re.compile(
    r"\b(?:vacas?|vaquinha|brincos?|animal|animais|n[uú]meros?|n)\s+(\d{1,6})\b",
    re.IGNORECASE)

# Continuação de grupo logo após o marcador: "vaca 22 e 23 e 40 ...".
# O número da continuação NÃO pode ser seguido de unidade — senão
# "vaca 22 e 300 quilos" viraria dois animais (22 e 300).
_UNIDADES_NAO_ANIMAL = r"(?:ml|mg|mcg|cc|ui|g|kg|quilos?|litros?|anos?|meses|dias?|horas?|vezes)"
_CONTINUACAO_GRUPO = re.compile(
    r"\s*(?:e|,)\s+(\d{1,6})\b(?!\s*" + _UNIDADES_NAO_ANIMAL + r")")

# Lista de pesos: "pesando 300 e 320 quilos", "peso de 480 e 500 kg".
_LISTA_PESOS = re.compile(
    r"\b(?:pesando|pesam|pesa|peso(?:s)?(?:\s+de)?)\s+"
    r"(\d{2,4}(?:\s+(?:e|,)\s+\d{2,4})+)\s*(?:kg|quilos?|k)?\b")


def _expandir_grupo(ids, trecho):
    """[(id, trecho_do_id), ...] para um grupo de animais no mesmo trecho.

    Se o trecho tem uma lista de pesos do MESMO tamanho do grupo, distribui um
    peso por animal, na ordem ("22 e 23 ... pesando 300 e 320" -> 22 pesa 300,
    23 pesa 320). Caso contrário, todos recebem o trecho igual.
    """
    if len(ids) == 1:
        return [(ids[0], trecho)]

    m = _LISTA_PESOS.search(trecho)
    if m:
        pesos = re.findall(r"\d{2,4}", m.group(1))
        if len(pesos) == len(ids):
            resultado = []
            for id_vaca, peso in zip(ids, pesos):
                individual = (trecho[:m.start()] +
                              ("peso %s quilos" % peso) +
                              trecho[m.end():]).strip()
                resultado.append((id_vaca, individual))
            return resultado

    return [(id_vaca, trecho) for id_vaca in ids]


def segmentar_por_animal(texto):
    """[(id_vaca, trecho), ...] na ordem em que os animais foram ditados.
    Lista vazia se nenhum número de animal for encontrado."""
    texto = normalizar_com_numeros(texto or "")
    if not texto:
        return []
    marcas = list(_MARCADOR.finditer(texto))
    if not marcas:
        return []

    bruto = []
    for i, marca in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)

        # Grupo: consome "e 23", "e 40"... logo após o primeiro número.
        ids = [marca.group(1)]
        pos = marca.end()
        while True:
            cont = _CONTINUACAO_GRUPO.match(texto, pos)
            if cont is None or cont.end() > fim:
                break
            ids.append(cont.group(1))
            pos = cont.end()

        trecho = texto[marca.start():fim].strip()
        bruto.extend(_expandir_grupo(ids, trecho))

    # Une trechos consecutivos do mesmo animal.
    unido = []
    for id_vaca, trecho in bruto:
        if unido and unido[-1][0] == id_vaca:
            unido[-1] = (id_vaca, (unido[-1][1] + " " + trecho).strip())
        else:
            unido.append((id_vaca, trecho))
    return unido
