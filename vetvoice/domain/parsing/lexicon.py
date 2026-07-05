"""
parsing/lexicon.py
------------------
O "BANCO DE PALAVRAS" do domínio veterinário (RF006). É DADO PURO: cada
vocabulário é uma lista de `Term` com nome canônico, sinônimos e metadados.

Para ensinar um termo novo ao parser, basta adicionar/editar um `Term` aqui —
nenhuma lógica precisa mudar. Os nomes canônicos são mantidos iguais aos que a
interface e o banco já usam (ex.: chips de diagnóstico, próxima ação).
"""

from vetvoice.domain.parsing.vocabulary import Term, Vocabulary

# ---------------------------------------------------------------------------
# PROCEDIMENTOS
# ---------------------------------------------------------------------------
PROCEDIMENTOS = Vocabulary([
    # IATF e "inseminação" caem no mesmo procedimento — IATF é o protocolo de
    # inseminação em tempo fixo. Resolve "José fez IATF".
    Term("Inseminação Artificial",
         ("inseminacao", "insemina", "iatf", "ia", "inseminar")),
    Term("Diagnóstico de Gestação",
         ("diagnostico de gestacao", "dg", "toque", "diagnostico gestacional")),
    Term("Palpação", ("palpacao", "palpar", "palpacao retal")),
    Term("Ultrassonografia", ("ultrassom", "ultrassonografia", "us")),
    Term("Vacinação", ("vacinacao", "vacina", "vacinar")),
    Term("Implante de Chip Hormonal", ("chip hormonal", "implante", "chip")),
    Term("Exame Ginecológico", ("exame ginecologico", "ginecologico")),
    Term("Exame Clínico", ("exame clinico", "exame")),
    Term("Tratamento de Mastite", ("tratamento de mastite",)),
    Term("Tratamento de Cetose", ("tratamento de cetose",)),
    Term("Casqueamento", ("casqueamento", "casquear")),
    Term("Acompanhamento de Parto", ("parto", "acompanhamento de parto")),
    Term("Secagem", ("secagem", "secar", "vaca seca")),
])

# ---------------------------------------------------------------------------
# STATUS REPRODUTIVO — só as duas opções da tela (Prenha / Vazia)
# ---------------------------------------------------------------------------
STATUS = Vocabulary([
    Term("Prenha", ("prenha", "prenhe", "gestante", "gravida", "positiva")),
    Term("Vazia", ("vazia", "negativa", "nao prenha")),
])

# ---------------------------------------------------------------------------
# DIAGNÓSTICOS — os canônicos batem com config.DIAGNOSTICO_OPCOES quando
# possível; os que não estão na lista caem em "Outro" na interface (RF009).
# ---------------------------------------------------------------------------
DIAGNOSTICOS = Vocabulary([
    Term("Sem alterações", ("sem alteracoes", "sem anormalidades", "normal")),
    Term("Mastite", ("mastite", "masite")),
    Term("Cetose Subclínica", ("cetose", "cetose subclinica")),
    Term("Retenção de Placenta", ("retencao de placenta", "placenta retida")),
    Term("Metrite", ("metrite", "endometrite")),
    Term("Claudicação", ("claudicacao", "manqueira", "manca")),
    Term("Prolapso Uterino", ("prolapso uterino", "prolapso")),
    # Fora da lista de chips -> viram "Outro" + texto livre na tela.
    Term("Hipocalcemia", ("hipocalcemia", "febre do leite")),
])

# ---------------------------------------------------------------------------
# MEDICAMENTOS — meta["dose_comum"] é só informativo/expansível.
# ---------------------------------------------------------------------------
MEDICAMENTOS = Vocabulary([
    Term("Flunixin Meglumine", ("flunixin", "flunixim", "flunixina", "banamine")),
    Term("Metronidazol", ("metronidazol", "metro", "metron")),
    Term("Oxitetraciclina", ("oxitetraciclina", "oxitetra", "terramicina")),
    Term("Penicilina", ("penicilina", "penicil")),
    Term("Enrofloxacino", ("enrofloxacino", "enrofloxacina", "baytril")),
    Term("Tilosina", ("tilosina",)),
    Term("Ceftiofur", ("ceftiofur", "ceftio")),
    Term("Meloxicam", ("meloxicam",)),
    Term("Dexametasona", ("dexametasona", "dexa")),
    Term("Corticoide", ("corticoide", "corticosteroide")),
    Term("Ivermectina", ("ivermectina", "ivomec")),
    Term("Dipirona", ("dipirona",)),
    Term("Ocitocina", ("ocitocina", "oxitocina")),
    Term("Prostaglandina", ("prostaglandina", "cloprostenol", "lutalyse")),
    Term("Cálcio", ("calcio", "gluconato de calcio")),
    Term("Propileno Glicol", ("propileno glicol",)),
    Term("Complexo Vitamínico", ("complexo vitaminico", "vitamina", "vitaminas")),
    Term("Antibiótico", ("antibiotico",)),
    Term("Anti-inflamatório", ("anti inflamatorio", "antiinflamatorio")),
    Term("Soro", ("soro",)),
    Term("Sêmen", ("semen", "smen")),
    Term("Vacina", ("vacina",)),
])

# ---------------------------------------------------------------------------
# RAÇAS
# ---------------------------------------------------------------------------
RACAS = Vocabulary([
    Term("Holandês", ("holandes", "holandesa", "holandes preto e branco")),
    Term("Girolando", ("girolando", "girolanda")),
    Term("Jersey", ("jersey", "jersei")),
    Term("Gir Leiteiro", ("gir leiteiro",)),
    Term("Gir", ("gir",)),
    Term("Nelore", ("nelore",)),
    Term("Angus", ("angus",)),
    Term("Brahman", ("brahman",)),
    Term("Senepol", ("senepol",)),
    Term("Pardo Suíço", ("pardo suico",)),
    Term("Guzerá", ("guzera",)),
    Term("Simental", ("simental",)),
    Term("Canchim", ("canchim",)),
])

# ---------------------------------------------------------------------------
# CATEGORIAS DO ANIMAL — hoje preenchem o campo "idade_anos" (que aceita texto)
# quando não há idade numérica. Modeladas como entidade própria para uma futura
# coluna "Categoria" no banco/planilha.
# ---------------------------------------------------------------------------
CATEGORIAS = Vocabulary([
    Term("Bezerra", ("bezerra", "terneira")),
    Term("Bezerro", ("bezerro", "terneiro")),
    Term("Novilha", ("novilha", "novilhas")),
    Term("Novilho", ("novilho",)),
    Term("Primípara", ("primipara",)),
    Term("Secundípara", ("secundipara",)),
    Term("Multípara", ("multipara",)),
    Term("Nulípara", ("nulipara",)),
    Term("Vaca seca", ("vaca seca",)),
    Term("Lactante", ("lactante", "em lactacao")),
    Term("Vaca adulta", ("vaca adulta",)),
])

# ---------------------------------------------------------------------------
# UNIDADES DE DOSE — usadas pelo extrator de medicação (regex).
# ---------------------------------------------------------------------------
UNIDADES_DOSE = ("ml", "mg", "mcg", "cc", "ui", "g")

# ---------------------------------------------------------------------------
# PRÓXIMA AÇÃO sugerida a partir do procedimento (inferência).
# Chaves = nomes canônicos de PROCEDIMENTOS.
# ---------------------------------------------------------------------------
PROXIMA_ACAO = {
    "Inseminação Artificial": "Retornar em ~30 dias para diagnóstico de gestação",
    "Diagnóstico de Gestação": "Reconfirmar gestação em 60 dias / acompanhar",
    "Palpação": "Reavaliar conforme achado da palpação",
    "Ultrassonografia": "Registrar idade gestacional e reavaliar conforme necessário",
    "Vacinação": "Anotar próxima dose no calendário sanitário",
    "Implante de Chip Hormonal": "Retirar/avaliar o implante no prazo do protocolo",
    "Tratamento de Mastite": "Reavaliar o quarto mamário em 3-5 dias",
    "Tratamento de Cetose": "Monitorar apetite e corpos cetônicos em 48h",
    "Acompanhamento de Parto": "Observar involução uterina e retenção de placenta",
}

# Vocabulários que participam da correção da transcrição exibida e da detecção
# de "termos clínicos" (palavras que não podem virar nome de fazenda/pessoa).
VOCABULARIOS_CLINICOS = (
    PROCEDIMENTOS, STATUS, DIAGNOSTICOS, MEDICAMENTOS, RACAS, CATEGORIAS,
)
