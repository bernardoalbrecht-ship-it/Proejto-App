"""
shared/config.py
----------------
Configurações centrais do VetVoice — caminhos, interruptores de funcionalidade,
credenciais e as colunas/opções usadas por toda a aplicação.

Por padrão o app roda em MODO OFFLINE/GRATUITO. Os recursos de nuvem (Google
Cloud Speech, GPT, Google Sheets) só ligam quando os interruptores abaixo forem
mudados para True e as credenciais forem preenchidas.
"""

import os
from pathlib import Path

# ----------------------------------------------------------------------------
# CAMINHOS DO PROJETO
# BASE_DIR = raiz do repositório (este arquivo fica em vetvoice/shared/).
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "dados"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "atendimentos.db"
CREDENTIALS_DIR = BASE_DIR / "credenciais"
CREDENTIALS_DIR.mkdir(exist_ok=True)

# Transcrições brutas da Ronda (fazenda inteira), uma por gravação — cópia de
# segurança em .txt antes de segmentar por animal e enviar à planilha.
RONDAS_DIR = DATA_DIR / "rondas"
RONDAS_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------------
# INTERRUPTORES DE FUNCIONALIDADE (liga/desliga recursos)
# ----------------------------------------------------------------------------
USAR_GOOGLE_CLOUD_SPEECH = False   # True = transcrição paga do Google Cloud
USAR_IA_OPENAI = False             # True = análise da fala com GPT (paga)
USAR_GOOGLE_SHEETS = False         # True = sincroniza com Google Sheets na nuvem

# Transcrição AO VIVO offline (Vosk). Cai para o modo reserva se indisponível.
USAR_VOSK_TEMPO_REAL = True
VOSK_MODEL_PATH = BASE_DIR / "assets" / "vosk" / "vosk-model-small-pt-0.3"

# ----------------------------------------------------------------------------
# IDIOMA E ÁUDIO
# ----------------------------------------------------------------------------
IDIOMA = "pt-BR"
TAXA_AMOSTRAGEM = 16000            # 16 kHz — padrão para reconhecimento de fala

# ----------------------------------------------------------------------------
# CREDENCIAIS (só usadas com os interruptores acima em True / login Google)
# ----------------------------------------------------------------------------
GOOGLE_CLOUD_CREDENTIALS = CREDENTIALS_DIR / "google_cloud.json"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODELO = "gpt-4o-mini"

GOOGLE_SHEETS_CREDENTIALS = CREDENTIALS_DIR / "google_sheets.json"

# Login com Google (OAuth) — planilha no próprio Drive do usuário.
GOOGLE_OAUTH_CLIENT = CREDENTIALS_DIR / "oauth_client.json"
GOOGLE_TOKEN_PATH = DATA_DIR / "google_token.json"
GOOGLE_SHEETS_INDEX = DATA_DIR / "google_sheets_index.json"
GOOGLE_OAUTH_SCOPES = (
    "openid email "
    "https://www.googleapis.com/auth/spreadsheets "
    "https://www.googleapis.com/auth/drive.file"
)

# ----------------------------------------------------------------------------
# COLUNAS DO REGISTRO (mesma ordem no banco e na planilha)
# ----------------------------------------------------------------------------
COLUNAS = [
    "id_vaca", "data", "hora", "veterinario", "propriedade", "tipo_producao",
    "procedimento", "raca", "peso_kg", "idade_anos", "status_reprodutivo",
    "diagnostico", "medicacoes", "proxima_acao", "observacoes",
    "transcricao_original", "sincronizado",
]

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
# OPÇÕES SELECIONÁVEIS (parser e interface concordam sobre os valores possíveis)
# ----------------------------------------------------------------------------
TIPO_PRODUCAO_OPCOES = ["Corte", "Leite"]

STATUS_REPRODUTIVO_OPCOES = ["Prenha", "Vazia"]

DIAGNOSTICO_OPCOES = [
    "Sem alterações", "Mastite", "Cetose Subclínica", "Retenção de Placenta",
    "Metrite", "Claudicação", "Prolapso Uterino", "Outro",
]

# Chips "de fábrica" para Raça e Procedimento. O usuário amplia essas listas
# pela opção "Outro" (os termos novos ficam salvos no banco — RF "dicionários
# editáveis") e o parser continua reconhecendo o vocabulário completo do léxico.
RACA_OPCOES = [
    "Nelore", "Angus", "Girolando", "Holandês", "Jersey", "Brahman", "Mestiço",
]

PROCEDIMENTO_OPCOES = [
    "Inseminação Artificial", "Diagnóstico de Gestação", "Vacinação",
    "Palpação", "Exame Clínico", "Casqueamento",
]

# Categorias de dicionário editável (usadas pela tela e pela persistência).
CATEGORIAS_DICIONARIO = ("raca", "procedimento", "diagnostico")
