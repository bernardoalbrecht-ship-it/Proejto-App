"""
composition.py — Composition Root
---------------------------------
Único lugar que conhece TODAS as camadas ao mesmo tempo. Monta as
implementações concretas (SQLite, Google, áudio, parser) e as injeta nos casos
de uso, entregando um `Servicos` pronto para a interface usar.

Trocar uma implementação (ex.: outro banco, outro parser, LLM na nuvem) é
mudar só aqui — nada mais no app precisa saber.
"""

from vetvoice.application.analise import AnalisarFala
from vetvoice.application.atendimentos import GestaoAtendimentos
from vetvoice.application.autenticacao import Autenticacao
from vetvoice.application.dicionarios import GestaoDicionarios
from vetvoice.application.propriedades import GestaoPropriedades
from vetvoice.application.servicos import Servicos
from vetvoice.application.sessao import Sessao
from vetvoice.application.sincronizacao import SincronizarAtendimentos
from vetvoice.domain.parsing import ParserHibridoOffline
from vetvoice.infrastructure.google.auth import AutenticadorGoogle
from vetvoice.infrastructure.google.sheets import ServicoNuvemGoogle
from vetvoice.infrastructure.persistence import sqlite
from vetvoice.infrastructure.speech.transcritor import TranscritorVoz
from vetvoice.shared import config


def _criar_parser():
    """Escolhe o parser: GPT (se ligado e com chave) com fallback offline;
    caso contrário, o parser híbrido offline."""
    offline = ParserHibridoOffline()
    if config.USAR_IA_OPENAI and config.OPENAI_API_KEY:
        # Importado só quando ligado, para não exigir o pacote openai no build.
        from vetvoice.infrastructure.nlp_openai import ParserOpenAI
        return ParserOpenAI(fallback=offline)
    return offline


def montar_servicos() -> Servicos:
    """Constrói o contêiner de casos de uso com as dependências reais."""
    sqlite.inicializar_banco()

    repo_atend = sqlite.RepositorioAtendimentosSQLite()
    repo_prop = sqlite.RepositorioPropriedadesSQLite()
    repo_dic = sqlite.RepositorioDicionariosSQLite()
    nuvem = ServicoNuvemGoogle()

    return Servicos(
        analise=AnalisarFala(_criar_parser()),
        atendimentos=GestaoAtendimentos(repo_atend),
        propriedades=GestaoPropriedades(repo_prop, repo_atend),
        dicionarios=GestaoDicionarios(repo_dic),
        sincronizacao=SincronizarAtendimentos(repo_atend, nuvem),
        autenticacao=Autenticacao(AutenticadorGoogle()),
        transcritor=TranscritorVoz(),
        sessao=Sessao(),
    )
