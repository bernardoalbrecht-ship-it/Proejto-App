"""
screens/configuracoes.py — Configurações e ajuda: modo de operação, aparência
(tema claro/escuro) e conta/nuvem.
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from vetvoice.presentation.dialogs import confirmar
from vetvoice.presentation.theme import CORES, TEMA, aplicar_tema, pintar_fundo, \
    rotulo_icone
from vetvoice.presentation.widgets import (
    Botao, Cartao, RolagemComCampos, SeletorOpcoes, chip, pagina, texto_livre,
    titulo_tela,
)

# Nome amigável de cada categoria editável (bate com config.CATEGORIAS_DICIONARIO)
_ROTULO_CATEGORIA = {
    "raca": "Raças",
    "procedimento": "Procedimentos",
    "diagnostico": "Diagnósticos",
}


class TelaConfig(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(titulo_tela("Ajustes", "Conta, aparência e ajuda"))

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=[dp(16), dp(8), dp(16),
                          dp(80)], spacing=dp(14), size_hint_y=None)  # folga p/ barra
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

        # Cartão dicionários editáveis (termos criados pelo usuário)
        dicion = Cartao()
        dicion.add_widget(texto_livre(
            "[b]%s[/b]" % rotulo_icone("prancheta", "Meus termos"),
            cor=CORES["texto"], tamanho="15sp", altura=dp(24)))
        dicion.add_widget(texto_livre(
            "Raças, procedimentos e diagnósticos que você adicionou pela opção "
            "\"Outro\" na ficha do atendimento.",
            cor=CORES["texto_suave"], tamanho="13sp", altura=dp(50)))
        botao_termos = Botao(texto=rotulo_icone("lupa", "Gerenciar meus termos"),
                             cor=CORES["verde_claro"], size_hint_y=None,
                             height=dp(46), font_size="14sp")
        botao_termos.bind(on_release=lambda *_: self._gerenciar_termos())
        dicion.add_widget(botao_termos)
        corpo.add_widget(dicion)

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

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _gerenciar_termos(self):
        """Popup listando os termos que o usuário criou, por categoria, cada um
        com um botão de lixeira."""
        conteudo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        pintar_fundo(conteudo, CORES["fundo"], raio=18)
        conteudo.add_widget(texto_livre(
            "[b]Meus termos[/b]", cor=CORES["verde"], tamanho="16sp",
            altura=dp(30)))
        conteudo.add_widget(texto_livre(
            "Remova o que não usa. As opções de fábrica não aparecem aqui.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(34)))

        scroll = RolagemComCampos()
        grade = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grade.bind(minimum_height=grade.setter("height"))
        scroll.add_widget(grade)
        conteudo.add_widget(scroll)

        botao_fechar = Botao(texto="Fechar", cor=CORES["marrom"],
                             size_hint_y=None, height=dp(46))
        conteudo.add_widget(botao_fechar)

        popup = Popup(title="", separator_height=0, content=conteudo,
                      size_hint=(0.92, 0.82), background="",
                      background_color=(0, 0, 0, 0.5))
        botao_fechar.bind(on_release=popup.dismiss)

        def recarregar():
            grade.clear_widgets()
            algum = False
            for categoria, rotulo in _ROTULO_CATEGORIA.items():
                termos = self.servicos.dicionarios.personalizados(categoria)
                if not termos:
                    continue
                algum = True
                grade.add_widget(texto_livre(
                    "[b]%s[/b]" % rotulo, cor=CORES["texto"], tamanho="14sp",
                    altura=dp(24)))
                for termo in termos:
                    grade.add_widget(self._linha_termo(categoria, termo,
                                                       recarregar))
            if not algum:
                vazio = Cartao(size_hint_y=None, height=dp(70))
                vazio.add_widget(texto_livre(
                    "Você ainda não criou termos.\nUse o chip \"Outro\" na ficha "
                    "do atendimento.", cor=CORES["texto_suave"], tamanho="13sp"))
                grade.add_widget(vazio)

        recarregar()
        popup.open()

    def _linha_termo(self, categoria, termo, apos_excluir):
        cartao = Cartao(orientation="horizontal", size_hint_y=None, height=dp(52),
                        padding=dp(12), spacing=dp(10))
        cartao.add_widget(texto_livre(termo, cor=CORES["texto"], tamanho="14sp"))
        lixeira = Botao(texto=rotulo_icone("lixeira", ""), cor=CORES["terracota"],
                        raio=10, size_hint=(None, None), width=dp(48),
                        height=dp(34), font_size="16sp")

        def excluir(*_):
            confirmar(
                "Remover termo",
                "Remover \"%s\" da sua lista? (Atendimentos já salvos não mudam.)"
                % termo,
                ao_confirmar=lambda: (
                    self.servicos.dicionarios.excluir(categoria, termo),
                    apos_excluir()))
        lixeira.bind(on_release=excluir)
        cartao.add_widget(lixeira)
        return cartao

    def _mudar_tema(self, opcao):
        aplicar_tema(escuro=(opcao == "Escuro"))
        # As cores foram "queimadas" nos widgets antigos: reconstruir tudo para
        # que nasçam com a paleta nova.
        App.get_running_app().reconstruir_telas(tela_atual="config")
