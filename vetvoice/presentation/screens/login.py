"""
screens/login.py — Login / cadastro (beta): nome simples ou "Entrar com Google".
"""

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from vetvoice.presentation.dialogs import aviso
from vetvoice.presentation.theme import (
    CORES, FONTE_ICONES, ICONES, pintar_fundo, rotulo_icone,
)
from vetvoice.presentation.widgets import Botao, Campo, Cartao, etiqueta, texto_livre


class TelaLogin(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical")
        pintar_fundo(raiz, CORES["fundo"], raio=0)

        # --- Terço superior: faixa verde com logo + nome ---
        topo = BoxLayout(orientation="vertical", size_hint_y=0.34,
                         padding=dp(16), spacing=dp(4))
        pintar_fundo(topo, CORES["verde"], raio=0)
        topo.add_widget(Widget())
        simbolo = Label(text=ICONES.get("vaca", "?"), font_size="64sp",
                        color=(1, 1, 1, 1), size_hint_y=None, height=dp(78),
                        halign="center", valign="middle")
        if FONTE_ICONES:
            simbolo.font_name = FONTE_ICONES
        simbolo.bind(size=simbolo.setter("text_size"))
        topo.add_widget(simbolo)
        nome = Label(text="[b]VetVoice[/b]", markup=True, font_size="30sp",
                     color=(1, 1, 1, 1), size_hint_y=None, height=dp(42),
                     halign="center", valign="middle")
        nome.bind(size=nome.setter("text_size"))
        topo.add_widget(nome)
        tag = Label(text="Atendimento veterinário por voz", font_size="12sp",
                    color=(1, 1, 1, 0.85), size_hint_y=None, height=dp(20),
                    halign="center", valign="middle")
        tag.bind(size=tag.setter("text_size"))
        topo.add_widget(tag)
        topo.add_widget(Widget())
        raiz.add_widget(topo)

        # --- Abaixo: cartão de login/cadastro ---
        meio = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(14))
        cartao = Cartao()
        cartao.add_widget(texto_livre("[b]Entrar[/b]", cor=CORES["texto"],
                                      tamanho="18sp", altura=dp(28)))
        cartao.add_widget(texto_livre(
            "Versão beta — cadastro simplificado.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(22)))

        cartao.add_widget(etiqueta("Seu nome"))
        self.campo_nome = Campo(multiline=False, hint_text="Ex: Dr. João",
                                size_hint_y=None, height=dp(46))
        cartao.add_widget(self.campo_nome)

        botao_entrar = Botao(texto=rotulo_icone("estetoscopio", "Entrar"),
                             cor=CORES["verde"], size_hint_y=None, height=dp(52),
                             font_size="16sp")
        botao_entrar.bind(on_release=self._entrar)
        cartao.add_widget(botao_entrar)

        botao_google = Botao(texto=rotulo_icone("nuvem_subir", "Entrar com Google"),
                             cor=CORES["azul"], size_hint_y=None, height=dp(52),
                             font_size="16sp")
        botao_google.bind(on_release=self._entrar_google)
        cartao.add_widget(botao_google)

        # Fallback: se o navegador não voltar sozinho para o app (loopback
        # bloqueado em alguns aparelhos), o usuário cola aqui o endereço que
        # abriu (começa com http://127.0.0.1) e conclui o login.
        cartao.add_widget(texto_livre(
            "[b]Ficou preso no navegador depois de autorizar?[/b] Acontece em "
            "alguns celulares: a página final (\"não é possível acessar o "
            "site\" ou parecida) não é um erro — é só o app não tendo voltado "
            "sozinho. Toque e segure a barra de endereço do navegador, copie o "
            "link inteiro (começa com http://127.0.0.1) e cole abaixo.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(84)))
        self.campo_code = Campo(multiline=False, size_hint_y=None, height=dp(44),
                                hint_text="Cole aqui o link copiado do navegador")
        cartao.add_widget(self.campo_code)
        botao_concluir = Botao(texto="Concluir login com esse link",
                               cor=CORES["verde_claro"], size_hint_y=None,
                               height=dp(46), font_size="13sp")
        botao_concluir.bind(on_release=self._concluir_manual)
        cartao.add_widget(botao_concluir)

        meio.add_widget(cartao)
        meio.add_widget(Widget())
        raiz.add_widget(meio)
        self.add_widget(raiz)

    def _entrar(self, *_):
        nome = self.campo_nome.text.strip()
        if not nome:
            aviso("Atenção", "Escreva seu nome para entrar (versão beta).")
            return
        self.servicos.sessao.usuario = nome
        self.servicos.sessao.nuvem = False
        self.manager.current = "inicial"

    def _entrar_google(self, *_):
        """Login REAL com Google (OAuth). Abre o navegador na tela de
        consentimento; ao voltar, o app cria/atualiza a planilha no Drive."""
        autenticacao = self.servicos.autenticacao
        sessao = self.servicos.sessao

        if autenticacao.esta_logado():
            sessao.usuario = autenticacao.email() or "Conta Google"
            sessao.nuvem = True
            self.manager.current = "inicial"
            return

        if not autenticacao.esta_configurado():
            aviso("Login com Google",
                  "O login com Google ainda não está configurado neste app "
                  "(faltam as credenciais OAuth). Enquanto isso, você pode usar "
                  "o app normalmente e sincronizar em modo local.")
            return

        aviso("Login com Google",
              "Vou abrir o navegador. Entre na sua conta Google, autorize e "
              "o app deve reabrir sozinho.\n\nSe isso não acontecer e o "
              "navegador ficar parado numa página, é só voltar aqui: mais "
              "abaixo nesta tela tem um campo para colar o endereço e "
              "concluir o login na mão.")

        autenticacao.login(callback_sucesso=self._ao_sucesso_login,
                           callback_erro=self._ao_erro_login)

    def _ao_sucesso_login(self, email):
        def _ui(*_):
            sessao = self.servicos.sessao
            sessao.usuario = email or "Conta Google"
            sessao.nuvem = True
            aviso("Conectado ao Google",
                  "Login concluído como:\n%s\n\nAgora o botão Sincronizar "
                  "cria/atualiza a planilha no seu Drive." % (email or "—"))
            self.manager.current = "inicial"
        Clock.schedule_once(_ui)

    def _ao_erro_login(self, msg):
        Clock.schedule_once(lambda *_: aviso(
            "Login com Google", "Não foi possível concluir o login.\n\n%s"
            % msg))

    def _concluir_manual(self, *_):
        entrada = self.campo_code.text.strip()
        if not entrada:
            aviso("Concluir login",
                  "Cole o endereço (ou o código) que apareceu no navegador "
                  "depois de você autorizar.")
            return
        self.servicos.autenticacao.completar_manual(
            entrada, callback_sucesso=self._ao_sucesso_login,
            callback_erro=self._ao_erro_login)
