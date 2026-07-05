"""
application/propriedades.py
---------------------------
Casos de uso das fazendas/propriedades: listar, adicionar e excluir. Excluir uma
propriedade apaga todos os atendimentos dela (regra existente preservada).
"""

from typing import List

from vetvoice.domain.ports import RepositorioAtendimentos, RepositorioPropriedades


class GestaoPropriedades:
    def __init__(self, repo_prop: RepositorioPropriedades,
                 repo_atend: RepositorioAtendimentos):
        self._repo_prop = repo_prop
        self._repo_atend = repo_atend

    def listar(self) -> List[str]:
        return self._repo_prop.listar()

    def adicionar(self, nome: str) -> None:
        self._repo_prop.adicionar(nome)

    def excluir(self, nome: str) -> int:
        """Apaga a fazenda e todos os atendimentos dela. Devolve quantos foram."""
        return self._repo_atend.excluir_da_propriedade(nome)
