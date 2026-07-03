"""
ai_analyzer.py
--------------
Pega o TEXTO transcrito e transforma em CAMPOS ORGANIZADOS (id da vaca,
procedimento, status, próxima ação, etc.).

Dois modos:
  1) MODO GRATUITO (padrão): usa REGRAS em português (procura palavras-chave).
     Não custa nada, funciona offline. Reconhece os procedimentos mais comuns
     em pecuária leiteira.
  2) MODO IA (pago): usa o GPT (OpenAI) para entender frases mais complexas.
     Ativa quando USAR_IA_OPENAI = True no config.py.

Em ambos os casos, o resultado é apenas uma SUGESTÃO — o veterinário sempre
revisa e confirma na tela antes de salvar.
"""

import re
from backend import config

# Tamanho mínimo de palavra-chave para tentar correspondência aproximada.
# Abaixo disso (ex.: "chip", "soro") só aceitamos escrita exata — palavras
# curtas têm alto risco de "quase bater" em outra coisa por acaso.
TAMANHO_MINIMO_PARA_FUZZY = 5


def _distancia_edicao(a: str, b: str) -> int:
    """Distância de Levenshtein (nº mínimo de letras a trocar/inserir/tirar
    para transformar 'a' em 'b'). Implementação própria, sem biblioteca
    externa — roda leve em qualquer aparelho, celular incluso."""
    if len(a) < len(b):
        a, b = b, a
    linha_anterior = list(range(len(b) + 1))
    for i, letra_a in enumerate(a, start=1):
        linha_atual = [i]
        for j, letra_b in enumerate(b, start=1):
            custo = 0 if letra_a == letra_b else 1
            linha_atual.append(min(
                linha_anterior[j] + 1,      # remoção
                linha_atual[j - 1] + 1,     # inserção
                linha_anterior[j - 1] + custo,  # substituição
            ))
        linha_anterior = linha_atual
    return linha_anterior[-1]


def _erros_tolerados(tamanho_chave: int) -> int:
    """Quanto maior a palavra, mais letras erradas ela pode tolerar sem virar
    outra palavra por acidente (ex.: 'vaca'->'vacina' NÃO pode ser aceito,
    mas 'flunixim'->'flunixin' sim)."""
    return 1 if tamanho_chave <= 8 else 2


def analisar(transcricao: str) -> dict:
    """Recebe o texto falado e devolve um dicionário com os campos sugeridos."""
    if config.USAR_IA_OPENAI and config.OPENAI_API_KEY:
        try:
            return _analisar_com_ia(transcricao)
        except Exception as erro:
            print(f"[AVISO] IA falhou ({erro}). Usando regras locais.")
    return _analisar_com_regras(transcricao)


# ---------------------------------------------------------------------------
# MODO GRATUITO — regras em português
# ---------------------------------------------------------------------------

# Palavras-chave -> nome do procedimento
PROCEDIMENTOS = {
    "inseminação": "Inseminação Artificial",
    "insemina": "Inseminação Artificial",
    "diagnóstico de gestação": "Diagnóstico de Gestação",
    "diagnostico de gestacao": "Diagnóstico de Gestação",
    "gestação": "Diagnóstico de Gestação",
    "ultrassom": "Ultrassonografia",
    "vacina": "Vacinação",
    "chip hormonal": "Implante de Chip Hormonal",
    "implante": "Implante de Chip Hormonal",
    "exame ginecológico": "Exame Ginecológico",
    "exame": "Exame Clínico",
    "mastite": "Tratamento de Mastite",
    "cetose": "Tratamento de Cetose",
    "casqueamento": "Casqueamento",
    "parto": "Acompanhamento de Parto",
    "secagem": "Secagem",
}

# Palavras-chave -> status reprodutivo (só existem duas opções na interface)
STATUS = {
    "vazia": "Vazia",
    "prenhe": "Prenha",
    "prenha": "Prenha",
    "gestante": "Prenha",
    "gestação confirmada": "Prenha",
    "grávida": "Prenha",
    "gravida": "Prenha",
}

# Palavras-chave -> diagnóstico (mesmas opções mostradas como chips na tela)
DIAGNOSTICOS = {
    "sem anormalidades": "Sem alterações",
    "sem alterações": "Sem alterações",
    "sem alteracoes": "Sem alterações",
    "mastite": "Mastite",
    "cetose": "Cetose Subclínica",
    "retenção de placenta": "Retenção de Placenta",
    "retencao de placenta": "Retenção de Placenta",
    "metrite": "Metrite",
    "claudicação": "Claudicação",
    "claudicacao": "Claudicação",
    "prolapso": "Prolapso Uterino",
}

# Palavras que indicam medicação/insumo aplicado. Cada item é uma palavra-chave
# a procurar no texto -> nome "bonito" para mostrar no campo de medicações.
MEDICACOES = {
    "sêmen": "Sêmen", "semen": "Sêmen",
    "vacina": "Vacina",
    "antibiótico": "Antibiótico", "antibiotico": "Antibiótico",
    "propileno glicol": "Propileno Glicol",
    "hormônio": "Hormônio", "hormonio": "Hormônio",
    "chip": "Chip Hormonal",
    "prostaglandina": "Prostaglandina",
    "ocitocina": "Ocitocina",
    "cálcio": "Cálcio", "calcio": "Cálcio",
    "anti-inflamatório": "Anti-inflamatório", "anti-inflamatorio": "Anti-inflamatório",
    "flunixim": "Flunixin Meglumine", "flunixina": "Flunixin Meglumine",
    "banamine": "Flunixin Meglumine (Banamine)",
    "meloxicam": "Meloxicam",
    "dexametasona": "Dexametasona",
    "corticoide": "Corticoide", "corticóide": "Corticoide",
    "corticosteroide": "Corticoide", "corticosteróide": "Corticoide",
    "corticoides": "Corticoide",
    "oxitetraciclina": "Oxitetraciclina",
    "penicilina": "Penicilina",
    "ivermectina": "Ivermectina",
    "dipirona": "Dipirona",
    "buscopan": "Buscopan",
    "soro": "Soro",
    "vitamina": "Complexo Vitamínico",
}

# Palavras-chave -> raça (nome padronizado). As raças mais comuns em gado
# leiteiro e de corte no Brasil. A busca aceita erro de transcrição.
RACAS = {
    "holandês": "Holandês", "holandes": "Holandês", "holandesa": "Holandês",
    "girolando": "Girolando", "girolanda": "Girolando",
    "jersey": "Jersey", "jérsei": "Jersey", "jersei": "Jersey",
    "gir": "Gir", "gir leiteiro": "Gir Leiteiro",
    "nelore": "Nelore",
    "angus": "Angus",
    "brahman": "Brahman",
    "senepol": "Senepol",
    "pardo suíço": "Pardo Suíço", "pardo suico": "Pardo Suíço",
    "guzerá": "Guzerá", "guzera": "Guzerá",
    "simental": "Simental",
    "canchim": "Canchim",
}


# Próxima ação sugerida conforme o procedimento
PROXIMA_ACAO = {
    "Inseminação Artificial": "Retornar em ~30 dias para diagnóstico de gestação",
    "Diagnóstico de Gestação": "Reconfirmar gestação em 60 dias / acompanhar",
    "Ultrassonografia": "Registrar idade gestacional e reavaliar conforme necessário",
    "Vacinação": "Anotar próxima dose no calendário sanitário",
    "Implante de Chip Hormonal": "Retirar/avaliar o implante no prazo do protocolo",
    "Tratamento de Mastite": "Reavaliar o quarto mamário em 3-5 dias",
    "Tratamento de Cetose": "Monitorar apetite e corpos cetônicos em 48h",
}


def _tokens(texto: str) -> list:
    """Quebra o texto em palavras, ignorando pontuação."""
    return re.findall(r"[a-zà-ÿ]+", texto.lower())


def _bate(texto: str, chave: str, tokens: list = None) -> bool:
    """'chave' aparece em 'texto'? Primeiro tenta um match EXATO (rápido, sem
    ambiguidade); se não achar, tenta um match APROXIMADO, para tolerar erros
    típicos do reconhecimento de voz (letra trocada, faltando, etc.)."""
    if chave in texto:
        return True

    if len(chave) < TAMANHO_MINIMO_PARA_FUZZY:
        return False  # chave curta demais: só aceita escrita exata

    if tokens is None:
        tokens = _tokens(texto)
    chave_tokens = chave.split()
    n = len(chave_tokens)
    if n == 0 or len(tokens) < n:
        return False

    tolerancia = _erros_tolerados(len(chave))
    for i in range(len(tokens) - n + 1):
        janela = " ".join(tokens[i:i + n])
        # Corta cedo se o tamanho já difere mais que a tolerância permitida
        if abs(len(janela) - len(chave)) > tolerancia:
            continue
        if _distancia_edicao(janela, chave) <= tolerancia:
            return True
    return False


def _vocabulario_conhecido() -> set:
    """Todas as palavras "de uma coisa só" (sem espaço) que o app conhece —
    usado para corrigir erros de transcrição no texto exibido."""
    vocabulario = set()
    for dicionario in (PROCEDIMENTOS, STATUS, DIAGNOSTICOS, MEDICACOES, RACAS):
        for chave in dicionario:
            if " " not in chave:
                vocabulario.add(chave)
    return vocabulario


def corrigir_transcricao(texto: str) -> str:
    """Corrige, no PRÓPRIO TEXTO exibido, palavras que provavelmente saíram
    erradas do reconhecimento de voz (ex.: "vasia" -> "vazia", "masite" ->
    "mastite"), comparando com o vocabulário de termos que o app conhece.

    IMPORTANTE — isto é uma correção por PROXIMIDADE DE ESCRITA, não um
    entendimento de contexto de verdade: troca uma palavra pela mais parecida
    do nosso dicionário quando a diferença é pequena (mesmas regras da busca
    aproximada usada para preencher os campos). O resto da frase, pontuação e
    capitalização originais são preservados.
    """
    if not texto:
        return texto

    vocabulario = _vocabulario_conhecido()

    def _corrigir_palavra(encontro):
        palavra = encontro.group(0)
        minuscula = palavra.lower()
        if minuscula in vocabulario or len(minuscula) < TAMANHO_MINIMO_PARA_FUZZY:
            return palavra

        melhor, melhor_distancia = None, None
        for candidato in vocabulario:
            tolerancia = _erros_tolerados(len(candidato))
            if abs(len(candidato) - len(minuscula)) > tolerancia:
                continue
            distancia = _distancia_edicao(minuscula, candidato)
            if distancia <= tolerancia and (melhor_distancia is None
                                            or distancia < melhor_distancia):
                melhor, melhor_distancia = candidato, distancia

        return melhor if melhor else palavra

    return re.sub(r"[a-zà-ÿ]+", _corrigir_palavra, texto, flags=re.IGNORECASE)


def _analisar_com_regras(transcricao: str) -> dict:
    texto = transcricao.lower()
    tokens = _tokens(texto)

    resultado = {
        "propriedade": _extrair_propriedade(texto),
        "id_vaca": _extrair_id_vaca(texto),
        "procedimento": "",
        "raca": "",
        "peso_kg": _extrair_peso(texto),
        "idade_anos": _extrair_idade(texto),
        "status_reprodutivo": "",
        "diagnostico": "",
        "medicacoes": "",
        "proxima_acao": "",
        "observacoes": "",
    }

    # Procedimento — procura a primeira palavra-chave que aparecer
    for chave, nome in PROCEDIMENTOS.items():
        if _bate(texto, chave, tokens):
            resultado["procedimento"] = nome
            break

    # Raça — primeira raça conhecida citada
    for chave, nome in RACAS.items():
        if _bate(texto, chave, tokens):
            resultado["raca"] = nome
            break

    # Status reprodutivo (apenas Prenha/Vazia, as duas opções da tela).
    # IMPORTANTE: tratar a NEGAÇÃO primeiro — "não prenha", "não gestante",
    # "não deu prenhe" significam VAZIA. Sem isto, a busca por "prenha"
    # bateria dentro de "não prenha" e marcaria Prenha por engano.
    if re.search(r"\b(n[ãa]o|nao)\s+\w*\s*(pren|gest|gr[áa]vid)", texto):
        resultado["status_reprodutivo"] = "Vazia"
    else:
        for chave, nome in STATUS.items():
            if _bate(texto, chave, tokens):
                resultado["status_reprodutivo"] = nome
                break

    # Diagnóstico: procura por uma das opções conhecidas (mesmas da tela).
    # Se nada bater, deixamos em branco — o veterinário escolhe manualmente
    # entre os chips, em vez de o campo ficar poluído com a frase inteira.
    for chave, nome in DIAGNOSTICOS.items():
        if _bate(texto, chave, tokens):
            resultado["diagnostico"] = nome
            break
    # Nenhum diagnóstico da lista bateu? Tenta um texto livre (vira "Outro").
    if not resultado["diagnostico"]:
        resultado["diagnostico"] = _extrair_diagnostico_livre(texto)

    # Medicações/insumos citados (evita falso positivo: medicação não vira
    # diagnóstico nem se mistura com outros campos)
    resultado["medicacoes"] = _extrair_medicacoes(texto, tokens)

    # Próxima ação sugerida
    resultado["proxima_acao"] = PROXIMA_ACAO.get(resultado["procedimento"], "")

    return resultado


# Palavras que anunciam o NOME DA PROPRIEDADE na fala.
_PALAVRAS_PROPRIEDADE = (
    "cabanha", "cabana", "fazenda", "sítio", "sitio", "propriedade",
    "granja", "haras", "estância", "estancia", "rancho", "chácara", "chacara",
)
# Palavras que ENCERRAM o nome da propriedade (conectores / resto da frase).
# Inclui verbos/termos clínicos que costumam vir logo após o nome — foi o que
# fazia "propriedade josé feito iatf" virar o nome inteiro; agora para em
# "feito"/"iatf" e devolve só "José".
_PARADAS_PROPRIEDADE = {
    "e", "na", "no", "da", "do", "de", "dentro", "vaca", "vaquinha", "brinco",
    "animal", "com", "que", "adicionar", "adiciona", "coloca", "colocar",
    "anota", "anotar", "registrar", "registra", "fiz", "apliquei", "feito",
    "fez", "fazer", "iatf", "ia", "prenha", "prenhe", "vazia", "diagnóstico",
    "diagnostico", "aplicar", "apliquei", "dei", "deu", "novilha", "primípara",
    "primipara", "multípara", "multipara",
}


def _palavra_clinica(token: str) -> bool:
    """True se a palavra é um termo clínico conhecido (procedimento, status,
    diagnóstico, medicação, raça) — não deve virar parte do nome da fazenda."""
    for dicionario in (PROCEDIMENTOS, STATUS, DIAGNOSTICOS, MEDICACOES, RACAS):
        for chave in dicionario:
            if " " not in chave and token == chave:
                return True
    return False


def _extrair_propriedade(texto: str) -> str:
    """Procura 'cabanha X', 'fazenda Boa Vista', 'sítio do João'... e devolve
    o nome (até 3 palavras), parando em conectores ('e', 'na', 'dentro',
    'vaca'...) e em termos clínicos ('iatf', 'feito', 'mastite'...). Devolve
    '' se não encontrar."""
    for palavra in _PALAVRAS_PROPRIEDADE:
        encontro = re.search(r"\b%s\s+(.+)" % palavra, texto)
        if not encontro:
            continue
        nome = []
        for token in _tokens(encontro.group(1)):
            if token in _PARADAS_PROPRIEDADE or _palavra_clinica(token):
                break
            nome.append(token)
            if len(nome) >= 3:
                break
        if nome:
            return " ".join(p.capitalize() for p in nome)
    return ""


# ---------------------------------------------------------------------------
# MEDICAÇÕES — reconhece QUALQUER remédio citado ao lado de uma dose, não só
# os do dicionário (ex.: "metronidazol 3ml" -> "Metronidazol 3ml").
# ---------------------------------------------------------------------------
_UNID_MED = r"(?:ml|mg|mcg|cc|ui|g)"

# Palavras que, mesmo perto de uma dose, NÃO são nome de medicação.
_NAO_E_DROGA = {
    "de", "da", "do", "com", "e", "que", "fiz", "apliquei", "dei", "deu",
    "dar", "via", "por", "uma", "um", "na", "no", "nas", "nos", "dose",
    "doses", "vaca", "vacas", "brinco", "animal", "hoje", "agora", "total",
    "cada", "apenas", "so", "só", "tomou", "recebeu", "aplicar", "pesa",
    "peso", "kg", "anos", "ano", "idade",
    # categorias do animal não são remédio (evita "Novilha 5ml")
    "bezerra", "bezerro", "terneira", "terneiro", "novilha", "novilhas",
    "novilho", "primípara", "primipara", "secundípara", "secundipara",
    "multípara", "multipara", "nulípara", "nulipara",
}


def _canonizar_droga(palavra: str) -> str:
    """Nome 'bonito' de uma droga: usa o nome canônico se ela (ou algo bem
    parecido) está no dicionário conhecido; senão capitaliza a própria palavra,
    para medicações fora da lista (como 'metronidazol') também entrarem."""
    p = palavra.lower()
    if p in MEDICACOES:
        return MEDICACOES[p]
    for chave, nome in MEDICACOES.items():
        if " " not in chave and len(chave) >= TAMANHO_MINIMO_PARA_FUZZY:
            tolerancia = _erros_tolerados(len(chave))
            if (abs(len(chave) - len(p)) <= tolerancia
                    and _distancia_edicao(p, chave) <= tolerancia):
                return nome
    return palavra[:1].upper() + palavra[1:]


def _extrair_medicacoes(texto: str, tokens: list) -> str:
    """Extrai as medicações citadas com suas doses. Além do dicionário de
    fármacos conhecidos, captura a palavra ao lado de uma dose — assim
    remédios fora da lista também entram. Ex.: 'metronidazol 3ml, 5ml de
    corticoide' -> 'Metronidazol 3ml, Corticoide 5ml'."""
    ordem = []          # nomes na ordem de aparição
    dose_de = {}        # nome -> dose

    def registrar(nome, dose=None):
        if not nome or nome.lower() in _NAO_E_DROGA:
            return
        if nome not in ordem:
            ordem.append(nome)
        if dose and nome not in dose_de:
            dose_de[nome] = dose

    # 1) Droga ANTES da dose: "metronidazol 3ml"
    for m in re.finditer(r"([a-zà-ÿ]{4,})\s+(\d+(?:[.,]\d+)?)\s*(%s)\b"
                         % _UNID_MED, texto):
        registrar(_canonizar_droga(m.group(1)), m.group(2) + m.group(3))
    # 2) Droga DEPOIS da dose: "5ml de corticoide" / "5 ml corticoide"
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(%s)\s+(?:de\s+)?([a-zà-ÿ]{4,})\b"
                         % _UNID_MED, texto):
        registrar(_canonizar_droga(m.group(3)), m.group(1) + m.group(2))
    # 3) Fármacos conhecidos citados SEM dose (ex.: "apliquei antibiótico").
    for chave, nome in MEDICACOES.items():
        if _bate(texto, chave, tokens):
            registrar(nome)

    partes = []
    for nome in ordem:
        dose = dose_de.get(nome)
        partes.append("%s %s" % (nome, dose) if dose else nome)
    return ", ".join(partes)


def _extrair_id_vaca(texto: str) -> str:
    """Procura padrões como 'vaca 123', 'brinco 123' ou o primeiro número."""
    padrao = re.search(r"(?:vaca|brinco|animal|número|numero)\s+(\d+)", texto)
    if padrao:
        return padrao.group(1)
    numero = re.search(r"\b(\d{1,6})\b", texto)  # qualquer número como reserva
    return numero.group(1) if numero else ""


# Números por extenso mais comuns na fala (idade do animal costuma ser baixa)
_NUMEROS_EXTENSO = {
    "um": "1", "uma": "1", "dois": "2", "duas": "2", "três": "3", "tres": "3",
    "quatro": "4", "cinco": "5", "seis": "6", "sete": "7", "oito": "8",
    "nove": "9", "dez": "10", "onze": "11", "doze": "12", "treze": "13",
    "quatorze": "14", "catorze": "14", "quinze": "15",
}


def _extrair_peso(texto: str) -> str:
    """Procura o peso: 'pesa 450 kg', '450 quilos', 'peso 380'..."""
    padrao = re.search(
        r"(?:pesa|peso(?:\s+de)?|com)\s+(\d{2,4})\s*(?:kg|quilos?|k)?", texto)
    if padrao:
        return padrao.group(1)
    padrao = re.search(r"(\d{2,4})\s*(?:kg|quilos?)", texto)
    return padrao.group(1) if padrao else ""


# Categorias/estágios do animal — quando não se diz a idade em números, o
# veterinário costuma dizer a categoria (novilha, primípara...). Reconhecemos
# e colocamos no campo Idade, que aceita texto.
_CATEGORIAS_ANIMAL = {
    "bezerra": "Bezerra", "bezerro": "Bezerro", "terneira": "Terneira",
    "terneiro": "Terneiro", "novilha": "Novilha", "novilhas": "Novilha",
    "novilho": "Novilho", "primípara": "Primípara", "primipara": "Primípara",
    "secundípara": "Secundípara", "secundipara": "Secundípara",
    "multípara": "Multípara", "multipara": "Multípara",
    "nulípara": "Nulípara", "nulipara": "Nulípara",
    "vaca adulta": "Vaca adulta",
}


def _extrair_idade(texto: str) -> str:
    """Procura a idade em anos ('3 anos', 'idade 4', 'com dois anos') OU, na
    falta de número, a CATEGORIA do animal ('novilha', 'primípara'...)."""
    padrao = re.search(r"(\d{1,2})\s*anos?\b", texto)
    if padrao:
        return padrao.group(1)
    # idade por extenso: 'dois anos', 'três anos'
    padrao = re.search(r"([a-zà-ÿ]+)\s+anos?\b", texto)
    if padrao and padrao.group(1) in _NUMEROS_EXTENSO:
        return _NUMEROS_EXTENSO[padrao.group(1)]
    padrao = re.search(r"idade\s+(?:de\s+)?(\d{1,2})", texto)
    if padrao:
        return padrao.group(1)
    # Sem número: tenta a categoria do animal.
    tokens = _tokens(texto)
    for chave, rotulo in _CATEGORIAS_ANIMAL.items():
        if _bate(texto, chave, tokens):
            return rotulo
    return ""


# Termos que costumam anunciar um diagnóstico dito em texto livre.
_ANUNCIO_DIAGNOSTICO = (
    "diagnóstico de", "diagnostico de", "diagnóstico", "diagnostico",
    "diagnostiquei", "suspeita de", "quadro de", "apresenta", "apresentou",
    "com quadro de",
)


def _extrair_diagnostico_livre(texto: str) -> str:
    """Quando NENHUM diagnóstico conhecido bate, tenta pegar o que foi dito em
    texto livre depois de 'diagnóstico', 'suspeita de'... (até 4 palavras,
    parando em conectores). Serve para marcar 'Outro' e escrever o texto."""
    paradas = {"e", "na", "no", "da", "do", "com", "que", "vaca", "fiz",
               "apliquei", "aplicar", "dei", "deu", "dar", "medicação",
               "medicacao", "prenha", "prenhe", "vazia", "próxima", "proxima",
               "ml", "mg", "cc", "ui", "mcg"}
    for anuncio in _ANUNCIO_DIAGNOSTICO:
        encontro = re.search(r"\b%s\s+(.+)" % re.escape(anuncio), texto)
        if not encontro:
            continue
        palavras = []
        for token in _tokens(encontro.group(1)):
            # Para em conectores, em medicações/termos clínicos conhecidos
            # (ex.: "penicilina") e nas unidades de dose.
            if token in paradas or _palavra_clinica(token):
                break
            palavras.append(token)
            if len(palavras) >= 4:
                break
        if palavras:
            frase = " ".join(palavras)
            return frase[:1].upper() + frase[1:]
    return ""


# ---------------------------------------------------------------------------
# MODO IA — OpenAI GPT (pago)
# ---------------------------------------------------------------------------
def _analisar_com_ia(transcricao: str) -> dict:
    from openai import OpenAI

    cliente = OpenAI(api_key=config.OPENAI_API_KEY)

    instrucao = (
        "Você é assistente de um veterinário de gado leiteiro no Brasil. "
        "A partir da frase falada, extraia um JSON com as chaves exatamente: "
        "propriedade, id_vaca, procedimento, status_reprodutivo, diagnostico, "
        "medicacoes, proxima_acao, observacoes. 'propriedade' é o nome da "
        "fazenda/cabanha citada. Responda SOMENTE o JSON, sem texto extra."
    )

    resposta = cliente.chat.completions.create(
        model=config.OPENAI_MODELO,
        messages=[
            {"role": "system", "content": instrucao},
            {"role": "user", "content": transcricao},
        ],
        temperature=0,
    )

    import json
    conteudo = resposta.choices[0].message.content.strip()
    conteudo = conteudo.replace("```json", "").replace("```", "").strip()
    dados = json.loads(conteudo)

    # Garante que todas as chaves existam
    for chave in ["propriedade", "id_vaca", "procedimento", "status_reprodutivo",
                  "diagnostico", "medicacoes", "proxima_acao", "observacoes"]:
        dados.setdefault(chave, "")
    return dados
