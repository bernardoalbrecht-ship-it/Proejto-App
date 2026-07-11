"""
application/servicos.py
-----------------------
Agrupa os casos de uso num único objeto injetável (`Servicos`). A interface
recebe este contêiner e chama os casos de uso — sem nunca instanciar
repositórios, parser ou serviços de nuvem por conta própria.
"""

from dataclasses import dataclass

from vetvoice.application.analise import AnalisarFala
from vetvoice.application.atendimentos import GestaoAtendimentos
from vetvoice.application.autenticacao import Autenticacao
from vetvoice.application.dicionarios import GestaoDicionarios
from vetvoice.application.propriedades import GestaoPropriedades
from vetvoice.application.sessao import Sessao
from vetvoice.application.sincronizacao import SincronizarAtendimentos
from vetvoice.domain.ports import Transcritor


@dataclass
class Servicos:
    analise: AnalisarFala
    atendimentos: GestaoAtendimentos
    propriedades: GestaoPropriedades
    dicionarios: GestaoDicionarios
    sincronizacao: SincronizarAtendimentos
    autenticacao: Autenticacao
    transcritor: Transcritor
    sessao: Sessao
