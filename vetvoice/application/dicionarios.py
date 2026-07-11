"""
application/dicionarios.py
--------------------------
Caso de uso das LISTAS EDITÁVEIS (raça, procedimento, diagnóstico...). Junta as
opções "de fábrica" (config) com os termos que o usuário criou pela opção
"Outro", sem duplicar e preservando a ordem: primeiro as de fábrica, depois as
do usuário. É o que sustenta os chips "+ Outro" da tela de atendimento.
"""

from typing import List

from vetvoice.domain.ports import RepositorioDicionarios


class GestaoDicionarios:
    def __init__(self, repo: RepositorioDicionarios):
        self._repo = repo

    def opcoes(self, categoria: str, base: List[str]) -> List[str]:
        """Opções de fábrica + termos do usuário (sem repetir)."""
        resultado = list(base)
        vistos = {t.lower() for t in resultado}
        for termo in self._repo.listar(categoria):
            if termo.lower() not in vistos:
                resultado.append(termo)
                vistos.add(termo.lower())
        return resultado

    def adicionar(self, categoria: str, termo: str) -> None:
        self._repo.adicionar(categoria, termo)

    def personalizados(self, categoria: str) -> List[str]:
        """Só os termos criados pelo usuário (para a tela de gerenciamento)."""
        return self._repo.listar(categoria)

    def excluir(self, categoria: str, termo: str) -> None:
        self._repo.excluir(categoria, termo)
