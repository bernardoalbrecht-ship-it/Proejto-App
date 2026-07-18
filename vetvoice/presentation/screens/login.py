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
from vetvoice.presentation.widgets import (
    Botao, BotaoGoogle, Campo, Cartao, RolagemComCampos, desfocar_campos,
    etiqueta, texto_livre,
)


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

        # --- Abaixo: cartão de login/cadastro (rolável, para o teclado nunca
        # esconder o botão Entrar) ---
        scroll = RolagemComCampos()
        meio = BoxLayout(orientation="vertical", padding=dp(22),
                         spacing=dp(14), size_hint_y=None)
        meio.bind(minimum_height=meio.setter("height"))
        cartao = Cartao()
        cartao.add_widget(texto_livre("[b]Entrar[/b]", cor=CORES["texto"],
                                      tamanho="18sp", altura=dp(28)))
        cartao.add_widget(texto_livre(
            "Versão beta — cadastro simplificado.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(22)))

        cartao.add_widget(etiqueta("Seu nome"))
        self.campo_nome = Campo(multiline=False, hint_text="Ex: Dr. João",
                                size_hint_y=None, height=dp(46))
        # Apertar "OK/Ir" no teclado também entra — caminho garantido mesmo se
        # o botão ficar atrás do teclado.
        self.campo_nome.bind(on_text_validate=self._entrar)
        cartao.add_widget(self.campo_nome)

        botao_entrar = Botao(texto=rotulo_icone("estetoscopio", "Entrar"),
                             cor=CORES["verde"], size_hint_y=None, height=dp(52),
                             font_size="16sp")
        botao_entrar.bind(on_release=self._entrar)
        cartao.add_widget(botao_entrar)

        botao_google = BotaoGoogle()
        botao_google.bind(on_release=self._entrar_google)
        cartao.add_widget(botao_google)

        # Fallback do loopback (alguns aparelhos não voltam sozinhos do
        # navegador): fica ESCONDIDO atrás de um toque em "Problemas para
        # entrar?" — quem loga normal nunca vê essa parte.
        self._link_ajuda = Botao(
            texto="Problemas para entrar com o Google?",
            cor=CORES["fundo"], cor_texto=CORES["texto_suave"],
            size_hint_y=None, height=dp(34), font_size="12sp")
        self._link_ajuda.bind(on_release=self._alternar_ajuda)
        cartao.add_widget(self._link_ajuda)

        self._caixa_ajuda = BoxLayout(orientation="vertical", spacing=dp(8),
                                      size_hint_y=None, height=0, opacity=0,
                                      disabled=True)
        self._caixa_ajuda.add_widget(texto_livre(
            "Se depois de autorizar o navegador mostrar uma página de erro "
            "(\"não é possível acessar o site\"), o login funcionou — só "
            "faltou voltar ao app. Copie o endereço da barra do navegador "
            "(começa com http://127.0.0.1) e cole aqui.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(72)))
        self.campo_code = Campo(multiline=False, size_hint_y=None, height=dp(44),
                                hint_text="Cole aqui o link copiado do navegador")
        self._caixa_ajuda.add_widget(self.campo_code)
        botao_concluir = Botao(texto="Concluir login com esse link",
                               cor=CORES["verde_claro"], size_hint_y=None,
                               height=dp(46), font_size="13sp")
        botao_concluir.bind(on_release=self._concluir_manual)
        self._caixa_ajuda.add_widget(botao_concluir)
        cartao.add_widget(self._caixa_ajuda)

        meio.add_widget(cartao)
        scroll.add_widget(meio)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _alternar_ajuda(self, *_):
        """Mostra/esconde o fallback de colar o link (altura + opacidade)."""
        escondida = self._caixa_ajuda.disabled
        self._caixa_ajuda.disabled = not escondida
        self._caixa_ajuda.opacity = 1 if escondida else 0
        self._caixa_ajuda.height = dp(178) if escondida else 0

    def _entrar(self, *_):
        # Fecha o teclado antes de tudo: no Android o teclado aberto cobre o
        # botão e a tela se reposiciona no meio do toque, fazendo o "soltar"
        # cair fora do botão (por isso "não acontecia nada" ao tocar Entrar).
        desfocar_campos(self)
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
