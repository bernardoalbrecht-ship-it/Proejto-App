"""
google_sheets_sync.py
---------------------
Envia os atendimentos guardados no aparelho para uma planilha na NUVEM
(Google Sheets). Cada PROPRIEDADE/FAZENDA ganha a sua própria planilha.

Como funciona a lógica "offline-first":
  - Tudo é salvo primeiro no banco local (sempre funciona).
  - Quando há internet, chamamos sincronizar() e só os registros ainda não
    enviados (sincronizado = 0) sobem para a planilha.
  - Após subir com sucesso, o registro é marcado como sincronizado no banco.

Este módulo só age de verdade quando USAR_GOOGLE_SHEETS = True no config.py.
No modo de teste ele apenas simula, para você não precisar configurar nada agora.
"""

from backend import config, database
from backend.config import COLUNAS, COLUNAS_EXIBICAO


def sincronizar(propriedade: str) -> dict:
    """
    Envia os atendimentos pendentes para a planilha da propriedade.
    Retorna um resumo: {enviados, erros, modo}.
    """
    pendentes = database.listar_nao_sincronizados()

    if not config.USAR_GOOGLE_SHEETS:
        # MODO DE TESTE: apenas simula, marcando como sincronizado localmente
        for atendimento in pendentes:
            database.marcar_como_sincronizado(atendimento.id_banco)
        return {"enviados": len(pendentes), "erros": 0, "modo": "simulado"}

    # MODO REAL
    try:
        planilha = _abrir_ou_criar_planilha(propriedade)
    except Exception as erro:
        return {"enviados": 0, "erros": 1, "modo": "real", "detalhe": str(erro)}

    enviados, erros = 0, 0
    for atendimento in pendentes:
        try:
            linha = [str(getattr(atendimento, coluna, "")) for coluna in COLUNAS]
            planilha.append_row(linha, value_input_option="USER_ENTERED")
            database.marcar_como_sincronizado(atendimento.id_banco)
            enviados += 1
        except Exception as erro:
            print(f"[ERRO] Falha ao enviar atendimento {atendimento.id_banco}: {erro}")
            erros += 1

    return {"enviados": enviados, "erros": erros, "modo": "real"}


def _abrir_ou_criar_planilha(propriedade: str):
    """Abre a planilha da propriedade no Google Sheets; cria se não existir."""
    import gspread
    from google.oauth2.service_account import Credentials

    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credenciais = Credentials.from_service_account_file(
        str(config.GOOGLE_SHEETS_CREDENTIALS), scopes=escopos
    )
    cliente = gspread.authorize(credenciais)

    nome = f"Atendimentos_{propriedade}".replace(" ", "_")

    try:
        documento = cliente.open(nome)
    except gspread.SpreadsheetNotFound:
        documento = cliente.create(nome)
        aba = documento.sheet1
        cabecalho = [COLUNAS_EXIBICAO[c] for c in COLUNAS]
        aba.append_row(cabecalho)
        return aba

    return documento.sheet1
