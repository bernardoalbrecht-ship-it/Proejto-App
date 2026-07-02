"""
google_sheets_sync.py
---------------------
Envia os atendimentos guardados no aparelho para uma planilha no Google
Sheets, DENTRO DO DRIVE DO PRÓPRIO USUÁRIO (via login com Google / OAuth).

Cada PROPRIEDADE/FAZENDA ganha a sua própria planilha. A cada sincronização,
os atendimentos ainda não enviados (sincronizado = 0) são acrescentados como
novas linhas — então a planilha "se atualiza" toda vez que você sincroniza.

Falamos com as APIs do Google por REST (urllib), sem bibliotecas pesadas.

Lógica "offline-first":
  - Tudo é salvo primeiro no banco local (sempre funciona).
  - Se o usuário estiver logado no Google, sincronizar() envia os pendentes.
  - Se NÃO estiver logado, cai no modo simulado (só marca como sincronizado
    localmente), para o app continuar utilizável sem a nuvem.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from backend import config, database, google_auth
from backend.config import COLUNAS, COLUNAS_EXIBICAO

_SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
_DRIVE_API = "https://www.googleapis.com/drive/v3/files"


def sincronizar(propriedade: str) -> dict:
    """Envia os atendimentos pendentes para a planilha da propriedade.
    Retorna um resumo: {enviados, erros, modo}."""
    pendentes = database.listar_nao_sincronizados()

    # Sem login no Google -> modo simulado (não trava o app).
    if not google_auth.esta_logado():
        for atendimento in pendentes:
            database.marcar_como_sincronizado(atendimento.id_banco)
        return {"enviados": len(pendentes), "erros": 0, "modo": "simulado"}

    token = google_auth.obter_token_valido()
    if not token:
        return {"enviados": 0, "erros": 1, "modo": "real",
                "detalhe": "Sessão do Google expirou. Entre novamente."}

    try:
        planilha_id = _abrir_ou_criar_planilha(propriedade, token)
    except Exception as erro:
        return {"enviados": 0, "erros": 1, "modo": "real", "detalhe": str(erro)}

    if not pendentes:
        return {"enviados": 0, "erros": 0, "modo": "real",
                "link": _link_planilha(planilha_id)}

    linhas = [[str(getattr(a, coluna, "") or "") for coluna in COLUNAS]
              for a in pendentes]
    try:
        _append_linhas(planilha_id, linhas, token)
    except Exception as erro:
        return {"enviados": 0, "erros": len(pendentes), "modo": "real",
                "detalhe": str(erro)}

    for atendimento in pendentes:
        database.marcar_como_sincronizado(atendimento.id_banco)

    return {"enviados": len(pendentes), "erros": 0, "modo": "real",
            "link": _link_planilha(planilha_id)}


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
    return "VacaVet - %s" % (propriedade or "Sem nome").strip()


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
    """Devolve o ID da planilha da propriedade, criando-a (com cabeçalho) na
    primeira vez. Guarda o ID num índice local para acelerar as próximas."""
    nome = _nome_planilha(propriedade)

    # 1) Já criamos antes? (índice local por aparelho)
    indice = _ler_indice()
    if nome in indice:
        return indice[nome]

    # 2) Procura no Drive uma planilha com esse nome criada por este app.
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

    # 3) Não existe: cria a planilha e escreve o cabeçalho.
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
