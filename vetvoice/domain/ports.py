"""
domain/ports.py
---------------
PORTAS (interfaces) do domínio. Definem O QUE a aplicação precisa do mundo
externo, sem dizer COMO — quem implementa é a camada de infraestrutura
(SQLite, Google, áudio...). Isso inverte a dependência: o domínio não conhece
detalhes de framework, e as implementações podem ser trocadas/testadas.
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from vetvoice.domain.entities import Atendimento


class RepositorioAtendimentos(ABC):
    """Persistência dos atendimentos (offline-first)."""

    @abstractmethod
    def salvar(self, atendimento: Atendimento) -> int: ...

    @abstractmethod
    def listar(self, limite: int = 100,
               id_vaca: Optional[str] = None) -> List[Atendimento]: ...

    @abstractmethod
    def listar_pendentes(self) -> List[Atendimento]: ...

    @abstractmethod
    def marcar_sincronizado(self, id_banco: int) -> None: ...

    @abstractmethod
    def excluir(self, id_banco: int) -> None: ...

    @abstractmethod
    def excluir_da_vaca(self, id_vaca: str) -> int: ...

    @abstractmethod
    def excluir_da_propriedade(self, propriedade: str) -> int: ...


class RepositorioPropriedades(ABC):
    """Cadastro de fazendas/propriedades."""

    @abstractmethod
    def adicionar(self, nome: str) -> None: ...

    @abstractmethod
    def listar(self) -> List[str]: ...


class ParserFala(ABC):
    """Interpreta a fala transcrita em campos de um atendimento."""

    @abstractmethod
    def analisar(self, transcricao: str) -> dict: ...

    @abstractmethod
    def corrigir_transcricao(self, texto: str) -> str: ...


class ServicoNuvem(ABC):
    """Envio dos atendimentos para a planilha na nuvem (Google Sheets)."""

    @abstractmethod
    def esta_disponivel(self) -> bool:
        """True se dá para enviar de verdade (usuário logado)."""

    @abstractmethod
    def enviar(self, propriedade: str,
               atendimentos: List[Atendimento]) -> dict:
        """Envia as linhas. Retorna {ok: bool, link?: str, detalhe?: str}."""


class Autenticador(ABC):
    """Login com a conta de nuvem do usuário (Google OAuth)."""

    @abstractmethod
    def esta_configurado(self) -> bool: ...

    @abstractmethod
    def esta_logado(self) -> bool: ...

    @abstractmethod
    def email_logado(self) -> str: ...

    @abstractmethod
    def login(self, callback_sucesso: Callable = None,
              callback_erro: Callable = None) -> None: ...

    @abstractmethod
    def logout(self) -> None: ...


class Transcritor(ABC):
    """Transcrição de voz (ao vivo, offline quando possível)."""

    @abstractmethod
    def disponivel_ao_vivo(self) -> bool: ...

    @abstractmethod
    def iniciar_ao_vivo(self, callback_parcial: Callable = None,
                        callback_final: Callable = None,
                        callback_erro: Callable = None):
        """Começa a ouvir. Devolve uma sessão com .parar()/.cancelar()."""

    @abstractmethod
    def mensagem_erro(self, codigo) -> str: ...
