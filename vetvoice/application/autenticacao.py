"""
application/autenticacao.py
---------------------------
Caso de uso de login na nuvem. Encapsula a porta `Autenticador` para a interface
não depender de detalhes do OAuth.
"""

from vetvoice.domain.ports import Autenticador


class Autenticacao:
    def __init__(self, autenticador: Autenticador):
        self._auth = autenticador

    def esta_configurado(self) -> bool:
        return self._auth.esta_configurado()

    def esta_logado(self) -> bool:
        return self._auth.esta_logado()

    def email(self) -> str:
        return self._auth.email_logado()

    def login(self, callback_sucesso=None, callback_erro=None) -> None:
        self._auth.login(callback_sucesso=callback_sucesso,
                         callback_erro=callback_erro)

    def logout(self) -> None:
        self._auth.logout()
