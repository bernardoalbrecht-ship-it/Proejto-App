"""
config.py
---------
Configurações centrais do sistema veterinário.

IMPORTANTE PARA INICIANTES:
Por padrão o app roda em MODO DE TESTE (offline, gratuito, sem nuvem).
Nesse modo:
  - A transcrição usa o reconhecimento gratuito do Google Web (só precisa de internet)
    ou permite digitar o texto manualmente.
  - A "IA" que preenche os campos usa regras locais em português (sem custo).
  - Os dados ficam só no computador, no banco SQLite.

Quando você quiser usar os recursos PAGOS/na nuvem (Google Cloud Speech + IA + Google
Sheets), basta mudar as opções abaixo de False para True e preencher as credenciais.
"""

import os
from pathlib import Path

# ----------------------------------------------------------------------------
# CAMINHOS DO PROJETO
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # pasta veterinaria/
DATA_DIR = BASE_DIR / "dados"                              # onde o banco fica salvo
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "atendimentos.db"              # banco SQLite local
CREDENTIALS_DIR = BASE_DIR / "credenciais"                # coloque os JSON do Google aqui
CREDENTIALS_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------------
# INTERRUPTORES DE FUNCIONALIDADE (liga/desliga recursos)
# Deixe tudo em False para testar de graça. Mude para True quando configurar a nuvem.
# ----------------------------------------------------------------------------
USAR_GOOGLE_CLOUD_SPEECH = False   # True = transcrição paga do Google Cloud
USAR_IA_OPENAI = False             # True = análise com GPT (paga)
USAR_GOOGLE_SHEETS = False         # True = sincroniza com Google Sheets na nuvem

# Transcrição AO VIVO (vai escrevendo a frase enquanto você fala), offline e
# gratuita, usando o Vosk. Roda leve no celular (modelo pequeno, ~50MB).
# Se o modelo não estiver baixado ou o pacote 'vosk' não estiver instalado,
# o app cai automaticamente para o modo antigo (grava e transcreve depois).
USAR_VOSK_TEMPO_REAL = True
VOSK_MODEL_PATH = BASE_DIR / "assets" / "vosk" / "vosk-model-small-pt-0.3"

# ----------------------------------------------------------------------------
# IDIOMA E ÁUDIO
# ----------------------------------------------------------------------------
IDIOMA = "pt-BR"                   # português do Brasil
TAXA_AMOSTRAGEM = 16000            # 16 kHz — padrão para reconhecimento de fala

# ----------------------------------------------------------------------------
# CREDENCIAIS (só usadas se os interruptores acima estiverem em True)
# ----------------------------------------------------------------------------
# Google Cloud: baixe o JSON da conta de serviço e coloque em credenciais/
GOOGLE_CLOUD_CREDENTIALS = CREDENTIALS_DIR / "google_cloud.json"

# OpenAI: coloque sua chave na variável de ambiente OPENAI_API_KEY
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODELO = "gpt-4o-mini"      # modelo mais barato e suficiente para esta tarefa

# Google Sheets: JSON da conta de serviço com acesso ao Drive/Sheets
GOOGLE_SHEETS_CREDENTIALS = CREDENTIALS_DIR / "google_sheets.json"

# ----------------------------------------------------------------------------
# COLUNAS DO REGISTRO (mesma ordem no banco e na planilha)
# ----------------------------------------------------------------------------
COLUNAS = [
    "id_vaca",
    "data",
    "hora",
    "veterinario",
    "propriedade",
    "tipo_producao",
    "procedimento",
    "raca",
    "peso_kg",
    "idade_anos",
    "status_reprodutivo",
    "diagnostico",
    "medicacoes",
    "proxima_acao",
    "observacoes",
    "transcricao_original",
    "sincronizado",
]

# Nomes bonitos para exibir na tela e no cabeçalho da planilha
COLUNAS_EXIBICAO = {
    "id_vaca": "ID da Vaca (brinco)",
    "data": "Data",
    "hora": "Hora",
    "veterinario": "Veterinário",
    "propriedade": "Propriedade",
    "tipo_producao": "Tipo de Produção",
    "procedimento": "Procedimento",
    "raca": "Raça",
    "peso_kg": "Peso (kg)",
    "idade_anos": "Idade (anos)",
    "status_reprodutivo": "Status Reprodutivo",
    "diagnostico": "Diagnóstico",
    "medicacoes": "Medicações",
    "proxima_acao": "Próxima Ação",
    "observacoes": "Observações",
    "transcricao_original": "Transcrição Original",
    "sincronizado": "Sincronizado",
}

# ----------------------------------------------------------------------------
# OPÇÕES SELECIONÁVEIS (usadas pela IA de regras E pela interface, para que
# os dois lados sempre concordem sobre os valores possíveis de cada campo)
# ----------------------------------------------------------------------------
TIPO_PRODUCAO_OPCOES = ["Corte", "Leite"]

STATUS_REPRODUTIVO_OPCOES = ["Prenha", "Vazia"]

DIAGNOSTICO_OPCOES = [
    "Sem alterações",
    "Mastite",
    "Cetose Subclínica",
    "Retenção de Placenta",
    "Metrite",
    "Claudicação",
    "Prolapso Uterino",
    "Outro",
]
