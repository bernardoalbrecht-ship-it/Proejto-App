"""
google/sheets.py
----------------
Envia atendimentos para uma planilha no Google Sheets, dentro do Drive do
PRÓPRIO usuário (via login OAuth). Cada propriedade/fazenda ganha a sua própria
planilha; a cada envio, as linhas são acrescentadas.

Falamos com as APIs do Google por REST (urllib), sem bibliotecas pesadas.

`ServicoNuvemGoogle` implementa a porta `ServicoNuvem`. Diferente da versão
antiga, ele NÃO lê o banco nem marca como sincronizado — isso é
responsabilidade do caso de uso `SincronizarAtendimentos`. Aqui só empurramos
as linhas dos atendimentos recebidos.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List

from vetvoice.domain.entities import Atendimento
from vetvoice.domain.ports import ServicoNuvem
from vetvoice.infrastructure.google import auth
from vetvoice.shared import config
from vetvoice.shared.config import COLUNAS, COLUNAS_EXIBICAO

_SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
_DRIVE_API = "https://www.googleapis.com/drive/v3/files"


# ---------------------------------------------------------------------------
# Chamadas REST auxiliares
# ---------------------------------------------------------------------------
def _requisicao(url, token, metodo="GET", corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    req.add_header("Authorization", "Bearer " + token)
    if dados is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "ignore")[:200]
        raise RuntimeError("Erro %s do Google: %s" % (erro.code, detalhe))


def _nome_planilha(propriedade: str) -> str:
    return "VetVoice - %s" % (propriedade or "Sem nome").strip()


def _link_planilha(planilha_id: str) -> str:
    return "https://docs.google.com/spreadsheets/d/%s" % planilha_id


def _ler_indice():
    try:
        with open(config.GOOGLE_SHEETS_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _salvar_indice(indice):
    try:
        with open(config.GOOGLE_SHEETS_INDEX, "w", encoding="utf-8") as f:
            json.dump(indice, f)
    except OSError:
        pass


def _abrir_ou_criar_planilha(propriedade: str, token: str) -> str:
    """ID da planilha da propriedade, criando-a (com cabeçalho) na 1ª vez."""
    nome = _nome_planilha(propriedade)

    indice = _ler_indice()
    if nome in indice:
        return indice[nome]

    consulta = ("name = '%s' and "
                "mimeType = 'application/vnd.google-apps.spreadsheet' and "
                "trashed = false") % nome.replace("'", "\\'")
    url = _DRIVE_API + "?" + urllib.parse.urlencode({
        "q": consulta, "spaces": "drive", "fields": "files(id,name)"})
    achados = _requisicao(url, token).get("files", [])
    if achados:
        indice[nome] = achados[0]["id"]
        _salvar_indice(indice)
        return achados[0]["id"]

    criada = _requisicao(_SHEETS_API, token, metodo="POST",
                         corpo={"properties": {"title": nome}})
    planilha_id = criada["spreadsheetId"]
    cabecalho = [COLUNAS_EXIBICAO[c] for c in COLUNAS]
    _append_linhas(planilha_id, [cabecalho], token)

    indice[nome] = planilha_id
    _salvar_indice(indice)
    return planilha_id


def _append_linhas(planilha_id: str, linhas, token: str):
    url = ("%s/%s/values/A1:append?%s" % (
        _SHEETS_API, planilha_id,
        urllib.parse.urlencode({"valueInputOption": "USER_ENTERED"})))
    _requisicao(url, token, metodo="POST", corpo={"values": linhas})


class ServicoNuvemGoogle(ServicoNuvem):
    """Implementação da porta `ServicoNuvem` sobre o Google Sheets."""

    def esta_disponivel(self) -> bool:
        return auth.esta_logado()

    def enviar(self, propriedade: str,
               atendimentos: List[Atendimento]) -> dict:
        token = auth.obter_token_valido()
        if not token:
            return {"ok": False,
                    "detalhe": "Sessão do Google expirou. Entre novamente."}
        try:
            planilha_id = _abrir_ou_criar_planilha(propriedade, token)
        except Exception as erro:
            return {"ok": False, "detalhe": str(erro)}

        if atendimentos:
            linhas = [[str(getattr(a, coluna, "") or "") for coluna in COLUNAS]
                      for a in atendimentos]
            try:
                _append_linhas(planilha_id, linhas, token)
            except Exception as erro:
                return {"ok": False, "detalhe": str(erro)}

        return {"ok": True, "link": _link_planilha(planilha_id)}
