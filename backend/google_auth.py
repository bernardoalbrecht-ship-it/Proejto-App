"""
google_auth.py
--------------
Login com a conta Google do usuário (OAuth 2.0) para o app poder criar e
atualizar uma planilha no PRÓPRIO Google Drive dele.

Não usamos bibliotecas pesadas (gspread / google-api-python-client): só a
biblioteca-padrão do Python (urllib, http.server, json, hashlib...) para não
pesar nem arriscar o build do APK. No Android, o navegador é aberto via
pyjnius; no computador, via módulo webbrowser.

Fluxo usado: "loopback" (o recomendado pelo Google para apps nativos):
  1) subimos um servidor HTTP local em 127.0.0.1:PORTA;
  2) abrimos o navegador na tela de consentimento do Google, pedindo que ele
     redirecione de volta para 127.0.0.1:PORTA depois do "Permitir";
  3) o servidor local captura o "code" do redirecionamento;
  4) trocamos o "code" por um token de acesso (+ refresh token) e guardamos.

Depois disso, obter_token_valido() devolve sempre um token válido (renovando
sozinho quando expira), que o google_sheets_sync usa para falar com as APIs.
"""

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from backend import config

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_EMAIL_URL = "https://openidconnect.googleapis.com/v1/userinfo"


# ---------------------------------------------------------------------------
# Estado / configuração
# ---------------------------------------------------------------------------
def _ler_config_cliente():
    """Lê o oauth_client.json (client_id/secret). Aceita tanto o formato
    {"installed": {...}} quanto {"web": {...}} baixado do Google Cloud."""
    try:
        with open(config.GOOGLE_OAUTH_CLIENT, "r", encoding="utf-8") as f:
            bruto = json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return None
    dados = bruto.get("installed") or bruto.get("web") or bruto
    if "client_id" in dados and "client_secret" in dados:
        return dados
    return None


def esta_configurado() -> bool:
    """True se o app tem as credenciais de OAuth (login com Google possível)."""
    return _ler_config_cliente() is not None


def _ler_token():
    try:
        with open(config.GOOGLE_TOKEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return None


def _salvar_token(token: dict):
    try:
        with open(config.GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as f:
            json.dump(token, f)
    except OSError:
        pass


def esta_logado() -> bool:
    token = _ler_token()
    return bool(token and token.get("refresh_token"))


def email_logado() -> str:
    token = _ler_token() or {}
    return token.get("email", "")


def logout():
    try:
        os.remove(config.GOOGLE_TOKEN_PATH)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# PKCE + montagem da URL de consentimento
# ---------------------------------------------------------------------------
def _pkce():
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    desafio = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, desafio


def _montar_url_auth(cfg, porta, desafio, state):
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": "http://127.0.0.1:%d/" % porta,
        "response_type": "code",
        "scope": config.GOOGLE_OAUTH_SCOPES,
        "code_challenge": desafio,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",   # queremos refresh_token
        "prompt": "consent",        # garante o refresh_token na 1ª vez
    }
    return _AUTH_URL + "?" + urllib.parse.urlencode(params)


# ---------------------------------------------------------------------------
# Servidor local que captura o redirecionamento com o "code"
# ---------------------------------------------------------------------------
class _ColetorCode(HTTPServer):
    code = None
    state_recebido = None
    evento = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        consulta = urllib.parse.urlparse(self.path).query
        campos = urllib.parse.parse_qs(consulta)
        self.server.code = (campos.get("code") or [None])[0]
        self.server.state_recebido = (campos.get("state") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body style='font-family:sans-serif;text-align:center;"
            "padding-top:60px'><h2>Login concluído ✅</h2><p>Pode fechar esta "
            "aba e voltar para o VetSheets.</p></body></html>".encode("utf-8"))
        if self.server.evento is not None:
            self.server.evento.set()

    def log_message(self, *args):
        pass  # silencia o log padrão do http.server


# ---------------------------------------------------------------------------
# Abrir o navegador (Android via Intent; desktop via webbrowser)
# ---------------------------------------------------------------------------
def _abrir_navegador(url: str):
    if "ANDROID_ARGUMENT" in os.environ:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread

        @run_on_ui_thread
        def _abrir():
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            PythonActivity.mActivity.startActivity(intent)
        _abrir()
    else:
        import webbrowser
        webbrowser.open(url)


# ---------------------------------------------------------------------------
# Troca de code por token e renovação
# ---------------------------------------------------------------------------
def _post_form(url, dados):
    corpo = urllib.parse.urlencode(dados).encode()
    req = urllib.request.Request(url, data=corpo, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _trocar_code_por_token(cfg, code, verifier, porta):
    return _post_form(_TOKEN_URL, {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": "http://127.0.0.1:%d/" % porta,
    })


def _buscar_email(access_token):
    req = urllib.request.Request(
        _EMAIL_URL, headers={"Authorization": "Bearer " + access_token})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp).get("email", "")
    except Exception:
        return ""


def obter_token_valido():
    """Devolve um access_token válido (renovando com o refresh_token se
    necessário). Retorna None se não estiver logado ou a renovação falhar."""
    token = _ler_token()
    if not token or not token.get("refresh_token"):
        return None

    if token.get("access_token") and token.get("expira_em", 0) > time.time() + 60:
        return token["access_token"]

    cfg = _ler_config_cliente()
    if not cfg:
        return None
    try:
        novo = _post_form(_TOKEN_URL, {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        })
    except Exception:
        return None

    token["access_token"] = novo.get("access_token", "")
    token["expira_em"] = time.time() + int(novo.get("expires_in", 3600))
    _salvar_token(token)
    return token["access_token"] or None


# ---------------------------------------------------------------------------
# Login interativo (roda numa thread; chama callbacks ao terminar)
# ---------------------------------------------------------------------------
def login(callback_sucesso=None, callback_erro=None, timeout: float = 300.0):
    cfg = _ler_config_cliente()
    if not cfg:
        if callback_erro:
            callback_erro("O login com Google ainda não foi configurado neste "
                          "app. (Falta o arquivo de credenciais OAuth.)")
        return

    def _fluxo():
        servidor = None
        try:
            servidor = _ColetorCode(("127.0.0.1", 0), _Handler)
            servidor.evento = threading.Event()
            porta = servidor.server_address[1]

            verifier, desafio = _pkce()
            state = secrets.token_urlsafe(16)
            url = _montar_url_auth(cfg, porta, desafio, state)

            # Atende exatamente um redirecionamento, numa thread própria.
            threading.Thread(target=servidor.handle_request, daemon=True).start()
            _abrir_navegador(url)

            if not servidor.evento.wait(timeout):
                raise TimeoutError("Tempo esgotado esperando o login no navegador.")
            if not servidor.code:
                raise RuntimeError("Login cancelado no navegador.")
            if servidor.state_recebido != state:
                raise RuntimeError("Falha de segurança na verificação do login.")

            resposta = _trocar_code_por_token(cfg, servidor.code, verifier, porta)
            refresh = resposta.get("refresh_token")
            access = resposta.get("access_token", "")
            if not refresh:
                raise RuntimeError("O Google não devolveu o token de acesso "
                                   "contínuo. Tente remover o app das permissões "
                                   "da conta e entrar de novo.")
            email = _buscar_email(access)
            _salvar_token({
                "refresh_token": refresh,
                "access_token": access,
                "expira_em": time.time() + int(resposta.get("expires_in", 3600)),
                "email": email,
            })
            if callback_sucesso:
                callback_sucesso(email)
        except Exception as erro:
            if callback_erro:
                callback_erro(str(erro))
        finally:
            if servidor is not None:
                try:
                    servidor.server_close()
                except Exception:
                    pass

    threading.Thread(target=_fluxo, daemon=True).start()
