"""
screens/splash.py — Tela de abertura (símbolo + nome por ~2s).
"""

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from vetvoice.presentation.theme import CORES, FONTE_ICONES, ICONES, pintar_fundo


class TelaSplash(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical")
        pintar_fundo(raiz, CORES["verde"], raio=0)

        raiz.add_widget(Widget())  # espaçador flexível

        simbolo = Label(text=ICONES.get("vaca", "?"), font_size="92sp",
                        color=(1, 1, 1, 1), size_hint_y=None, height=dp(110),
                        halign="center", valign="middle")
        if FONTE_ICONES:
            simbolo.font_name = FONTE_ICONES
        simbolo.bind(size=simbolo.setter("text_size"))
        raiz.add_widget(simbolo)

        nome = Label(text="[b]VetVoice[/b]", markup=True, font_size="32sp",
                     color=(1, 1, 1, 1), size_hint_y=None, height=dp(46),
                     halign="center", valign="middle")
        nome.bind(size=nome.setter("text_size"))
        raiz.add_widget(nome)

        tagline = Label(text="Atendimento veterinário por voz",
                        font_size="13sp", color=(1, 1, 1, 0.85),
                        size_hint_y=None, height=dp(22),
                        halign="center", valign="middle")
        tagline.bind(size=tagline.setter("text_size"))
        raiz.add_widget(tagline)

        raiz.add_widget(Widget())

        self.add_widget(raiz)
        self._evento_transicao = None

    def on_enter(self):
        self._evento_transicao = Clock.schedule_once(self._ir_para_login, 2.0)

    def on_leave(self):
        if self._evento_transicao:
            self._evento_transicao.cancel()

    def _ir_para_login(self, *_):
        if self.manager:
            # Se já logado nesta sessão, pula direto para o app.
            self.manager.current = ("inicial" if self.servicos.sessao.usuario
                                    else "login")
