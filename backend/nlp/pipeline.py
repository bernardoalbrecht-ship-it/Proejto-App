"""
nlp/pipeline.py
---------------
Orquestra o parser híbrido. Segue a PRIORIDADE definida no PRD:

    1) Dicionário  -> termos conhecidos (procedimento, raça, status, diagnóstico)
    2) Regex       -> números e associação medicamento<->dose (id, peso, idade)
    3) Contexto    -> nome da propriedade a partir de palavras-gatilho
    4) Inferência  -> diagnóstico livre ("Outro") e próxima ação

O resultado é um dicionário com EXATAMENTE as mesmas chaves do parser antigo,
para ser um substituto direto (a interface e os testes continuam funcionando).
"""

import re

from backend.nlp import extractors, lexicon
from backend.nlp.text import normalizar, tokenizar
from backend.nlp import fuzzy

# Ordem/keys do resultado — contrato público do parser.
CAMPOS = (
    "propriedade", "id_vaca", "procedimento", "raca", "peso_kg", "idade_anos",
    "status_reprodutivo", "diagnostico", "medicacoes", "proxima_acao",
    "observacoes",
)


def _detectar_status(texto: str, tokens: list) -> str:
    """Status reprodutivo, tratando a NEGAÇÃO primeiro: 'não prenha', 'não deu
    prenhe' significam VAZIA. Sem isto, 'prenha' bateria dentro de 'não prenha'."""
    if re.search(r"\b(nao)\s+\w*\s*(pren|gest|gravid)", texto):
        return "Vazia"
    termo = lexicon.STATUS.encontrar(texto, tokens)
    return termo.canonico if termo else ""


def analisar(transcricao: str) -> dict:
    """Recebe a fala transcrita e devolve os campos sugeridos do atendimento."""
    texto = normalizar(transcricao)
    tokens = texto.split()

    resultado = {campo: "" for campo in CAMPOS}

    # 1) DICIONÁRIO — termos conhecidos.
    proc = lexicon.PROCEDIMENTOS.encontrar(texto, tokens)
    resultado["procedimento"] = proc.canonico if proc else ""

    raca = lexicon.RACAS.encontrar(texto, tokens)
    resultado["raca"] = raca.canonico if raca else ""

    resultado["status_reprodutivo"] = _detectar_status(texto, tokens)

    diag = lexicon.DIAGNOSTICOS.encontrar(texto, tokens)
    resultado["diagnostico"] = diag.canonico if diag else ""

    # 2) REGEX — números e medicação/dose.
    resultado["id_vaca"] = extractors.extrair_id_vaca(texto)
    resultado["peso_kg"] = extractors.extrair_peso(texto)
    resultado["idade_anos"] = extractors.extrair_idade_ou_categoria(texto, tokens)
    resultado["medicacoes"] = extractors.extrair_medicacoes(texto, tokens)

    # 3) CONTEXTO — nome da propriedade.
    resultado["propriedade"] = extractors.extrair_propriedade(texto)

    # 4) INFERÊNCIA — diagnóstico livre ("Outro") e próxima ação.
    if not resultado["diagnostico"]:
        resultado["diagnostico"] = extractors.extrair_diagnostico_livre(texto)
    resultado["proxima_acao"] = lexicon.PROXIMA_ACAO.get(
        resultado["procedimento"], "")

    return resultado


# ---------------------------------------------------------------------------
# CORREÇÃO DA TRANSCRIÇÃO EXIBIDA
# ---------------------------------------------------------------------------
def _vocabulario_corrigivel() -> set:
    """Palavras de UMA palavra que o app conhece — base para corrigir a fala."""
    vocab = set()
    for v in lexicon.VOCABULARIOS_CLINICOS:
        vocab |= v.sinonimos_de_palavra_unica()
    return vocab


def corrigir_transcricao(texto: str) -> str:
    """Corrige, no PRÓPRIO TEXTO exibido, palavras que provavelmente saíram
    erradas do reconhecimento de voz ('vasia' -> 'vazia'), comparando por
    PROXIMIDADE DE ESCRITA com o vocabulário conhecido. Pontuação, acentos e
    capitalização originais das demais palavras são preservados.

    Atenção: é correção por semelhança de escrita, não entendimento de
    contexto — troca uma palavra pela mais parecida quando a diferença é pequena.
    """
    if not texto:
        return texto
    vocabulario = _vocabulario_corrigivel()

    def _corrigir(encontro):
        palavra = encontro.group(0)
        minuscula = normalizar(palavra)
        if minuscula in vocabulario or len(minuscula) < fuzzy.TAMANHO_MINIMO_PARA_FUZZY:
            return palavra
        melhor, melhor_dist = None, None
        for candidato in vocabulario:
            tol = fuzzy.erros_tolerados(len(candidato))
            if abs(len(candidato) - len(minuscula)) > tol:
                continue
            dist = fuzzy.distancia_edicao(minuscula, candidato)
            if dist <= tol and (melhor_dist is None or dist < melhor_dist):
                melhor, melhor_dist = candidato, dist
        return melhor if melhor else palavra

    return re.sub(r"[a-zà-ÿ]+", _corrigir, texto, flags=re.IGNORECASE)
