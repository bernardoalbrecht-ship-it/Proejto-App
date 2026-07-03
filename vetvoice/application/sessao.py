"""
application/sessao.py
---------------------
Estado da sessão atual (fazenda, tipo de produção, usuário logado e um comando
de voz pendente). Substitui os dicionários globais SESSAO/PREFILL_COMANDO que
antes viviam soltos na interface.
"""

from dataclasses import dataclass

from vetvoice.shared import config


@dataclass
class Sessao:
    """Dados que persistem enquanto o app está aberto (não vão ao banco)."""
    propriedade: str = ""
    tipo_producao: str = config.TIPO_PRODUCAO_OPCOES[1]  # "Leite"
    usuario: str = ""
    nuvem: bool = False
    # Comando de voz interpretado na tela inicial e ainda não aplicado; a tela
    # de Atendimento o consome no on_pre_enter para já abrir preenchida.
    prefill_comando: str = ""

    def consumir_prefill(self) -> str:
        """Devolve o comando pendente e o limpa (só é aplicado uma vez)."""
        comando = self.prefill_comando
        self.prefill_comando = ""
        return comando
