"""
parsing/extractors.py
---------------------
Extratores baseados em REGEX + CONTEXTO — a parte do parser que lida com o que
os dicionários não cobrem: números (id, peso, idade), a associação
medicamento<->dose, o nome da propriedade e o diagnóstico dito em texto livre.

Todos recebem o texto JÁ NORMALIZADO (minúsculo, sem acento) e são funções
puras: mesma entrada, mesma saída, sem estado global.
"""

import re

from vetvoice.domain.parsing import lexicon
from vetvoice.domain.parsing.text import NUMEROS_POR_EXTENSO, numero_por_extenso

# Alternância de unidades de dose, ex.: "(?:ml|mg|mcg|cc|ui|g)"
_UNID = "(?:%s)" % "|".join(lexicon.UNIDADES_DOSE)
# Um valor de dose: número (3 / 3,5) OU número por extenso (tres, meia...).
# Ordena por tamanho para o regex casar a palavra mais longa primeiro.
_PALAVRAS_NUM = "|".join(sorted(NUMEROS_POR_EXTENSO, key=len, reverse=True))
_VALOR = r"(?:\d+(?:[.,]\d+)?|%s)" % _PALAVRAS_NUM


def _valor_para_texto(valor: str) -> str:
    """Normaliza o valor de uma dose para exibição: '3,5' -> '3.5',
    'tres' -> '3', 'meia' -> '0.5'."""
    n = numero_por_extenso(valor)
    if n is not None:
        return str(int(n)) if float(n).is_integer() else str(n)
    return valor.replace(",", ".")


# ---------------------------------------------------------------------------
# ID DA VACA
# ---------------------------------------------------------------------------
def extrair_id_vaca(texto: str) -> str:
    """'vaca 123', 'brinco 123', 'animal 123' ou, como reserva, o primeiro
    número que NÃO seja uma dose/peso/idade (evita pegar o '3' de '3 ml')."""
    explicito = re.search(r"(?:vaca|brinco|animal|numero|n)\s+(\d{1,6})", texto)
    if explicito:
        return explicito.group(1)
    reserva = re.search(
        r"\b(\d{1,6})\b(?!\s*(?:%s|kg|quilos?|anos?|ano))" % "|".join(
            lexicon.UNIDADES_DOSE), texto)
    return reserva.group(1) if reserva else ""


# ---------------------------------------------------------------------------
# PESO
# ---------------------------------------------------------------------------
def extrair_peso(texto: str) -> str:
    """'pesa 450', 'peso de 450 kg', '450 quilos'..."""
    p = re.search(r"(?:pesa|peso(?:\s+de)?)\s+(\d{2,4})\s*(?:kg|quilos?|k)?", texto)
    if p:
        return p.group(1)
    p = re.search(r"(\d{2,4})\s*(?:kg|quilos?)\b", texto)
    return p.group(1) if p else ""


# ---------------------------------------------------------------------------
# IDADE (número em anos) OU CATEGORIA do animal (novilha, primípara...)
# ---------------------------------------------------------------------------
def extrair_idade_ou_categoria(texto: str, tokens: list) -> str:
    """Idade em anos ('3 anos', 'dois anos', 'idade 4') e, na falta de número,
    a CATEGORIA do animal ('novilha', 'primípara'...) — que também vai neste
    campo, pois ele aceita texto."""
    p = re.search(r"(\d{1,2})\s*anos?\b", texto)
    if p:
        return p.group(1)
    p = re.search(r"([a-z]+)\s+anos?\b", texto)
    if p:
        n = numero_por_extenso(p.group(1))
        if n is not None:
            return str(int(n))
    p = re.search(r"idade\s+(?:de\s+)?(\d{1,2})", texto)
    if p:
        return p.group(1)
    termo = lexicon.CATEGORIAS.encontrar(texto, tokens)
    return termo.canonico if termo else ""


# ---------------------------------------------------------------------------
# MEDICAÇÕES + DOSES  (dicionário + regex — o coração da associação)
# ---------------------------------------------------------------------------
# Palavras que, mesmo ao lado de uma dose, NÃO são nome de medicação.
_NAO_E_DROGA = {
    "de", "da", "do", "com", "e", "que", "fiz", "apliquei", "dei", "deu",
    "dar", "via", "por", "uma", "um", "na", "no", "nas", "nos", "dose",
    "doses", "vaca", "vacas", "brinco", "animal", "hoje", "agora", "total",
    "cada", "apenas", "so", "tomou", "recebeu", "aplicar", "pesa", "peso",
    "kg", "anos", "ano", "idade",
}
# Categorias do animal e status reprodutivo também não são remédio
# (evita "Novilha 5ml" e "Prenha 5ml").
_NAO_E_DROGA |= lexicon.CATEGORIAS.sinonimos_de_palavra_unica()
_NAO_E_DROGA |= lexicon.STATUS.sinonimos_de_palavra_unica()


def _canonizar_droga(palavra: str) -> str:
    """Nome canônico da droga se ela (ou algo bem próximo) está no dicionário;
    senão capitaliza a própria palavra (medicações fora da lista também entram
    — ex.: 'metronidazol' mesmo que não estivesse cadastrado)."""
    termo = lexicon.MEDICAMENTOS.casar_palavra(palavra)
    if termo:
        return termo.canonico
    return palavra[:1].upper() + palavra[1:]


def extrair_medicacoes(texto: str, tokens: list) -> str:
    """Medicações citadas com suas doses. Combina três estratégias:
      1) droga ANTES da dose  -> 'metronidazol 3ml'
      2) dose ANTES da droga  -> '5ml de corticoide'
      3) fármaco conhecido SEM dose -> 'apliquei antibiótico'
    Doses por extenso ('três ml') são convertidas para número."""
    ordem = []       # nomes na ordem de aparição
    dose_de = {}     # nome canônico -> dose formatada

    def registrar(nome, dose=None):
        if not nome or nome.lower() in _NAO_E_DROGA:
            return
        if nome not in ordem:
            ordem.append(nome)
        if dose and nome not in dose_de:
            dose_de[nome] = dose

    # 1) droga antes da dose
    for m in re.finditer(r"([a-z]{4,})\s+(%s)\s*(%s)\b" % (_VALOR, _UNID), texto):
        registrar(_canonizar_droga(m.group(1)),
                  _valor_para_texto(m.group(2)) + m.group(3))
    # 2) dose antes da droga
    for m in re.finditer(r"(%s)\s*(%s)\s+(?:de\s+)?([a-z]{4,})\b"
                         % (_VALOR, _UNID), texto):
        registrar(_canonizar_droga(m.group(3)),
                  _valor_para_texto(m.group(1)) + m.group(2))
    # 3) fármacos conhecidos citados sem dose
    for termo in lexicon.MEDICAMENTOS.encontrar_todos(texto, tokens):
        registrar(termo.canonico)

    partes = []
    for nome in ordem:
        dose = dose_de.get(nome)
        partes.append("%s %s" % (nome, dose) if dose else nome)
    return ", ".join(partes)


# ---------------------------------------------------------------------------
# PROPRIEDADE (contexto: palavra-gatilho + parada em conectores/termos clínicos)
# ---------------------------------------------------------------------------
_GATILHOS_PROPRIEDADE = (
    "cabanha", "cabana", "fazenda", "sitio", "propriedade", "granja", "haras",
    "estancia", "rancho", "chacara",
)
_PARADAS_PROPRIEDADE = {
    "e", "na", "no", "da", "do", "de", "dentro", "vaca", "vaquinha", "brinco",
    "animal", "com", "que", "adicionar", "adiciona", "coloca", "colocar",
    "anota", "anotar", "registrar", "registra", "fiz", "apliquei", "feito",
    "fez", "fazer", "aplicar", "dei", "deu",
}


def _e_termo_clinico(token: str) -> bool:
    """True se a palavra é um termo clínico conhecido (procedimento, status,
    diagnóstico, medicação, raça, categoria) — não pode entrar num nome."""
    for vocab in lexicon.VOCABULARIOS_CLINICOS:
        if token in vocab.sinonimos_de_palavra_unica():
            return True
    return False


def extrair_propriedade(texto: str) -> str:
    """'cabanha X', 'fazenda Boa Vista', 'sítio do João'... Devolve o nome (até
    3 palavras), parando em conectores e termos clínicos. '' se não achar."""
    for gatilho in _GATILHOS_PROPRIEDADE:
        m = re.search(r"\b%s\s+(.+)" % gatilho, texto)
        if not m:
            continue
        nome = []
        for token in re.findall(r"[a-z]+", m.group(1)):
            if token in _PARADAS_PROPRIEDADE or _e_termo_clinico(token):
                break
            nome.append(token)
            if len(nome) >= 3:
                break
        if nome:
            return " ".join(p.capitalize() for p in nome)
    return ""


# ---------------------------------------------------------------------------
# DIAGNÓSTICO EM TEXTO LIVRE (fallback -> "Outro")
# ---------------------------------------------------------------------------
_ANUNCIO_DIAGNOSTICO = (
    "diagnostico de", "diagnostico", "diagnostiquei", "suspeita de",
    "quadro de", "apresenta", "apresentou",
)
_PARADAS_DIAGNOSTICO = {
    "e", "na", "no", "da", "do", "com", "que", "vaca", "fiz", "apliquei",
    "aplicar", "dei", "deu", "dar", "medicacao", "prenha", "prenhe", "vazia",
    "proxima", "ml", "mg", "cc", "ui", "mcg", "g",
}


def extrair_diagnostico_livre(texto: str) -> str:
    """Quando nenhum diagnóstico conhecido bate, pega o que foi dito após
    'diagnóstico', 'suspeita de'... (até 4 palavras). Serve para o 'Outro'."""
    for anuncio in _ANUNCIO_DIAGNOSTICO:
        m = re.search(r"\b%s\s+(.+)" % re.escape(anuncio), texto)
        if not m:
            continue
        palavras = []
        for token in re.findall(r"[a-z]+", m.group(1)):
            if token in _PARADAS_DIAGNOSTICO or _e_termo_clinico(token):
                break
            palavras.append(token)
            if len(palavras) >= 4:
                break
        if palavras:
            frase = " ".join(palavras)
            return frase[:1].upper() + frase[1:]
    return ""
