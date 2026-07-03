"""
screens/configuracoes.py — Configurações e ajuda: modo de operação, aparência
(tema claro/escuro) e conta/nuvem.
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from vetvoice.presentation.theme import CORES, TEMA, aplicar_tema, rotulo_icone
from vetvoice.presentation.widgets import (
    Botao, Cartao, RolagemComCampos, SeletorOpcoes, cabecalho, chip, pagina,
    texto_livre,
)


class TelaConfig(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(cabecalho("Configurações", "Ajuda e modo de operação",
                                  icone_nome="engrenagem", com_voltar=True))

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(14),
                          size_hint_y=None)
        corpo.bind(minimum_height=corpo.setter("height"))

        # Cartão modo atual
        atual = Cartao()
        cabeca = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        cabeca.add_widget(texto_livre("[b]Modo de teste[/b]", cor=CORES["texto"],
                                      tamanho="16sp", altura=dp(28)))
        cabeca.add_widget(Widget())
        cabeca.add_widget(chip("GRÁTIS", CORES["chip_ok"], CORES["verde_escuro"]))
        atual.add_widget(cabeca)
        atual.add_widget(texto_livre(
            "• Voz ao vivo pelo reconhecimento do próprio Android (funciona "
            "offline se o pacote de voz em português estiver instalado).\n"
            "• Preenchimento por regras locais em português.\n"
            "• Dados salvos apenas neste aparelho (SQLite).",
            cor=CORES["texto_suave"], tamanho="13sp", altura=dp(90)))
        corpo.add_widget(atual)

        # Cartão aparência (tema claro/escuro)
        aparencia = Cartao()
        aparencia.add_widget(texto_livre("[b]Aparência[/b]", cor=CORES["texto"],
                                         tamanho="15sp", altura=dp(22)))
        seletor_tema = SeletorOpcoes(
            ["Claro", "Escuro"],
            valor_inicial="Escuro" if TEMA["escuro"] else "Claro",
            ao_selecionar=self._mudar_tema)
        aparencia.add_widget(seletor_tema)
        corpo.add_widget(aparencia)

        # Cartão conta / nuvem
        nuvem = Cartao()
        nuvem.add_widget(texto_livre("[b]%s[/b]" %
                                     rotulo_icone("nuvem_subir", "Conta e nuvem"),
                                     cor=CORES["azul"], tamanho="15sp",
                                     altura=dp(24)))
        usuario = self.servicos.sessao.usuario or "não conectado"
        nuvem.add_widget(texto_livre(
            "Conta: [b]%s[/b]" % usuario,
            cor=CORES["texto_suave"], tamanho="13sp", altura=dp(22)))
        botao_conta = Botao(texto=rotulo_icone("nuvem_subir", "Entrar / trocar conta"),
                            cor=CORES["azul"], size_hint_y=None, height=dp(46),
                            font_size="14sp")
        botao_conta.bind(on_release=lambda *_: setattr(self.manager,
                                                       "current", "login"))
        nuvem.add_widget(botao_conta)
        corpo.add_widget(nuvem)

        # Cartão dica
        dica = Cartao(cor=CORES["chip_pend"], borda=False)
        dica.add_widget(texto_livre(
            "%s  [b]Dica:[/b] se o microfone não funcionar, digite a frase no "
            % rotulo_icone("lampada", "").rstrip() +
            "campo de transcrição e toque em 'Preencher campos'. Funciona igual.",
            cor=CORES["marrom"], tamanho="13sp", altura=dp(50)))
        corpo.add_widget(dica)

        botao_voltar = Botao(texto="Voltar", cor=CORES["marrom"],
                             size_hint_y=None, height=dp(50))
        botao_voltar.bind(on_release=lambda *_: setattr(self.manager,
                                                        "current", "inicial"))
        corpo.add_widget(botao_voltar)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _mudar_tema(self, opcao):
        aplicar_tema(escuro=(opcao == "Escuro"))
        # As cores foram "queimadas" nos widgets antigos: reconstruir tudo para
        # que nasçam com a paleta nova.
        App.get_running_app().reconstruir_telas(tela_atual="config")
