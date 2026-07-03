"""
presentation/widgets.py
-----------------------
Componentes visuais reutilizáveis (cartões, botões "pill", campos, chips,
"segmented control", botão de gravação, cabeçalho...). Toda a aparência vem do
módulo `theme`; aqui fica o comportamento dos widgets.
"""

from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from vetvoice.presentation.theme import (
    CORES, escurecer, icone, pintar_fundo, rotulo_icone,
)


class Cartao(BoxLayout):
    """Caixa arredondada, como um card de site. Dentro de um ScrollView todo
    filho precisa ter altura definida; por padrão o cartão se ajusta ao
    conteúdo, mas respeita uma 'height' fixa se o chamador passar."""
    def __init__(self, cor=None, raio=18, borda=True, **kwargs):
        altura_fixa = "height" in kwargs
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(16))
        kwargs.setdefault("spacing", dp(10))
        super().__init__(**kwargs)
        pintar_fundo(self, cor or CORES["cartao"], raio,
                     borda=CORES["borda"] if borda else None)
        if not altura_fixa:
            self.size_hint_y = None
            self.bind(minimum_height=self.setter("height"))


class CartaoClicavel(ButtonBehavior, Cartao):
    """Cartao que responde a toque (cards do histórico)."""
    def on_press(self):
        if hasattr(self, "_cor_inst"):
            self._cor_antes_do_toque = tuple(self._cor_inst.rgba)
            self._cor_inst.rgba = escurecer(self._cor_antes_do_toque, 0.95)

    def on_release(self):
        if hasattr(self, "_cor_antes_do_toque"):
            self._cor_inst.rgba = self._cor_antes_do_toque


class Botao(ButtonBehavior, Label):
    """Botão "pill" estilizado (desenha o próprio fundo em canvas.before).
    Nunca chame pintar_fundo() sobre um Botao — use o parâmetro `borda`."""
    def __init__(self, texto="", cor=None, cor_texto=(1, 1, 1, 1),
                 raio=16, borda=None, **kwargs):
        kwargs.setdefault("markup", True)
        kwargs.setdefault("font_size", "16sp")
        super().__init__(text=texto, **kwargs)
        self.bold = True
        self.color = cor_texto
        self._cor = cor or CORES["verde"]
        self._raio = raio
        with self.canvas.before:
            self._c = Color(*self._cor)
            self._r = RoundedRectangle(radius=[raio])
            if borda is not None:
                self._c_borda = Color(*borda)
                self._linha = Line(width=1.2)
            else:
                self._linha = None
        self.bind(pos=self._att, size=self._att)

    def _att(self, *_):
        self._r.pos = self.pos
        self._r.size = self.size
        if self._linha is not None:
            x, y = self.pos
            w, h = self.size
            self._linha.rounded_rectangle = (x, y, w, h, self._raio)

    def on_press(self):
        self._c.rgba = escurecer(self._cor)

    def on_release(self):
        self._c.rgba = self._cor

    def piscar(self, cor_flash=(1, 1, 1, 0.55), duracao=0.12):
        """Brilho rápido de 'toque registrado' (chips/segmented control)."""
        original = self._c.rgba
        self._c.rgba = cor_flash
        Animation(rgba=original, duration=duracao, t="out_quad").start(self._c)


class Campo(TextInput):
    """Campo de texto com fundo nativo e contorno suave. Usamos o fundo NATIVO
    do TextInput (não pintar_fundo), senão o texto/cursor somem."""
    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_color", CORES["cartao"])
        kwargs.setdefault("foreground_color", CORES["texto_campo"])
        kwargs.setdefault("cursor_color", CORES["verde"])
        kwargs.setdefault("cursor_width", dp(3))
        kwargs.setdefault("cursor_blink", True)
        kwargs.setdefault("selection_color", (0.298, 0.686, 0.490, 0.35))
        kwargs.setdefault("hint_text_color", CORES["texto_suave"])
        kwargs.setdefault("padding", [dp(12), dp(10)])
        kwargs.setdefault("font_size", "16sp")
        super().__init__(**kwargs)


class RolagemComCampos(ScrollView):
    """ScrollView que dá foco IMEDIATO a um campo de texto ao ser tocado (o
    teclado do Android abre no 1º toque e continua aberto ao soltar o dedo).
    Botões, que herdam de ButtonBehavior, não precisam desse tratamento."""
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            alvo = self._alvo_sob_toque(self, touch.pos[0], touch.pos[1])
            if alvo is not None:
                alvo.focus = True
                touch.push()
                touch.apply_transform_2d(self.to_local)
                try:
                    alvo.on_touch_down(touch)
                finally:
                    touch.pop()
                return True
        return super().on_touch_down(touch)

    def _alvo_sob_toque(self, widget, tx, ty):
        for filho in widget.children:
            achado = self._alvo_sob_toque(filho, tx, ty)
            if achado is not None:
                return achado
        if isinstance(widget, TextInput) and not widget.disabled:
            wx, wy = widget.to_window(widget.x, widget.y)
            if wx <= tx <= wx + widget.width and wy <= ty <= wy + widget.height:
                return widget
        return None


def desfocar_campos(widget):
    """Tira o foco de todo campo de texto (recolhe o teclado antes de gravar)."""
    for filho in widget.children:
        desfocar_campos(filho)
    if isinstance(widget, TextInput) and widget.focus:
        widget.focus = False


class BotaoGravarRedondo(ButtonBehavior, Widget):
    """Botão de gravação estilo "câmera": círculo vermelho que vira quadrado ao
    gravar (toque para parar). Sobre ButtonBehavior — dispara com toque simples
    dentro do ScrollView, sem segurar o dedo (toggle controlado pelo callback)."""
    def __init__(self, ao_tocar=None, diametro=dp(76), **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self.size = (diametro, diametro)
        self._ao_tocar = ao_tocar
        self._gravando = False
        with self.canvas:
            self._cor_anel = Color(*CORES["borda"])
            self._anel = Line(width=dp(2.5))
            self._cor_miolo = Color(*CORES["terracota"])
            self._miolo = RoundedRectangle(radius=[diametro / 2.0])
        self.bind(pos=self._att, size=self._att)
        self._att()

    def _att(self, *_):
        x, y = self.pos
        w, h = self.size
        self._anel.circle = (x + w / 2.0, y + h / 2.0, w / 2.0 - dp(2))
        if self._gravando:
            lado = w * 0.42
            self._miolo.pos = (x + (w - lado) / 2.0, y + (h - lado) / 2.0)
            self._miolo.size = (lado, lado)
            self._miolo.radius = [dp(6)]
        else:
            margem = dp(8)
            self._miolo.pos = (x + margem, y + margem)
            self._miolo.size = (w - 2 * margem, h - 2 * margem)
            self._miolo.radius = [(w - 2 * margem) / 2.0]

    def set_gravando(self, gravando):
        self._gravando = bool(gravando)
        self._att()

    def on_press(self):
        self._cor_miolo.rgba = escurecer(CORES["terracota"])

    def on_release(self):
        self._cor_miolo.rgba = CORES["terracota"]
        desfocar_campos(Window)
        try:
            Window.release_all_keyboards()
        except Exception:
            pass
        if self._ao_tocar is not None:
            self._ao_tocar(self)


class ControleGravacao(BoxLayout):
    """Botão redondo de gravar + legenda que alterna entre repouso e 'ouvindo'."""
    def __init__(self, ao_tocar=None, rotulo="GRAVAR E FALAR", **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(112))
        kwargs.setdefault("spacing", dp(6))
        super().__init__(**kwargs)
        self._rotulo_idle = rotulo

        centro = AnchorLayout(anchor_x="center", anchor_y="center",
                              size_hint_y=None, height=dp(84))
        self.botao = BotaoGravarRedondo(ao_tocar=ao_tocar)
        centro.add_widget(self.botao)
        self.add_widget(centro)

        self.rotulo = Label(text=rotulo, markup=True, bold=True,
                            color=CORES["texto"], font_size="13sp",
                            size_hint_y=None, height=dp(20),
                            halign="center", valign="middle")
        self.rotulo.bind(size=self.rotulo.setter("text_size"))
        self.add_widget(self.rotulo)

    def set_estado(self, gravando):
        self.botao.set_gravando(gravando)
        if gravando:
            self.rotulo.text = "OUVINDO — TOQUE PARA PARAR"
            self.rotulo.color = CORES["verde"]
        else:
            self.rotulo.text = self._rotulo_idle
            self.rotulo.color = CORES["texto"]


def etiqueta(texto):
    """Legenda pequena em maiúsculas sobre os campos."""
    lbl = Label(text=texto.upper(), markup=True, color=CORES["texto_suave"],
                font_size="11sp", bold=True, halign="left", valign="middle",
                size_hint_y=None, height=dp(18))
    lbl.bind(size=lbl.setter("text_size"))
    return lbl


def texto_livre(txt, cor=None, tamanho="14sp", altura=None, bold=False):
    lbl = Label(text=txt, markup=True, color=cor or CORES["texto"],
                font_size=tamanho, bold=bold, halign="left", valign="middle")
    if altura is not None:
        lbl.size_hint_y = None
        lbl.height = altura
    lbl.bind(size=lbl.setter("text_size"))
    return lbl


def chip(texto, cor_fundo, cor_texto, icone_nome=None):
    """Cápsula colorida com texto e, opcionalmente, um ícone à esquerda."""
    caixa = BoxLayout(size_hint=(None, None), height=dp(26),
                      padding=[dp(10), 0], spacing=dp(4))
    caixa.width = dp(11) * len(texto) + dp(24) + (dp(16) if icone_nome else 0)
    pintar_fundo(caixa, cor_fundo, raio=13)
    if icone_nome:
        ic = icone(icone_nome, tamanho="13sp", cor=cor_texto)
        ic.pos_hint = {"center_y": 0.5}
        caixa.add_widget(ic)
    lbl = Label(text=texto, markup=True, color=cor_texto, font_size="12sp",
                bold=True)
    caixa.add_widget(lbl)
    return caixa


class SeletorOpcoes(GridLayout):
    """"Segmented control": linha/grade de botões onde só uma opção fica
    destacada por vez (Corte/Leite, Prenha/Vazia, Diagnóstico, fazendas...)."""
    def __init__(self, opcoes, valor_inicial="", ao_selecionar=None,
                 cols=2, altura_linha=dp(42), **kwargs):
        kwargs.setdefault("spacing", dp(8))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("cols", cols)
        kwargs.setdefault("row_default_height", altura_linha)
        kwargs.setdefault("row_force_default", True)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))

        self._ao_selecionar = ao_selecionar
        self._valor = valor_inicial
        self._botoes = {}

        for opcao in opcoes:
            botao = Botao(texto=opcao, cor=CORES["cartao"],
                          cor_texto=CORES["texto_suave"], raio=14,
                          borda=CORES["borda"], font_size="13sp")
            botao.bind(on_release=lambda _b, o=opcao: self.selecionar(o))
            self._botoes[opcao] = botao
            self.add_widget(botao)

        self._atualizar_destaque()

    @property
    def valor(self):
        return self._valor

    def selecionar(self, opcao, disparar_callback=True):
        self._valor = opcao
        self._atualizar_destaque()
        botao = self._botoes.get(opcao)
        if botao is not None:
            botao.piscar()
        if disparar_callback and self._ao_selecionar:
            self._ao_selecionar(opcao)

    def _atualizar_destaque(self):
        for opcao, botao in self._botoes.items():
            ativo = (opcao == self._valor)
            cor = CORES["verde"] if ativo else CORES["cartao"]
            botao._cor = cor
            botao._c.rgba = cor
            botao.color = (1, 1, 1, 1) if ativo else CORES["texto_suave"]


def ir_inicial(*_):
    App.get_running_app().root.current = "inicial"


def cabecalho(titulo, subtitulo="", icone_nome="vaca", com_voltar=False):
    """Barra superior verde com marca do app e (opcional) botão de voltar."""
    barra = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(78),
                      padding=[dp(14), dp(10)], spacing=dp(10))
    pintar_fundo(barra, CORES["verde"], raio=0)

    if com_voltar:
        voltar = Botao(texto=rotulo_icone("voltar", ""), cor=CORES["verde_escuro"],
                       raio=14, size_hint=(None, 1), width=dp(46), font_size="22sp")
        voltar.bind(on_release=ir_inicial)
        barra.add_widget(voltar)

    marca = BoxLayout(orientation="vertical", spacing=dp(2))
    linha = BoxLayout(orientation="horizontal", spacing=dp(8),
                      size_hint_y=None, height=dp(30))
    linha.add_widget(icone(icone_nome, tamanho="22sp", cor=(1, 1, 1, 1)))
    linha.add_widget(texto_livre("[b]%s[/b]" % titulo, cor=(1, 1, 1, 1),
                                 tamanho="20sp", altura=dp(30)))
    marca.add_widget(linha)
    if subtitulo:
        marca.add_widget(texto_livre(subtitulo, cor=(1, 1, 1, 0.8),
                                     tamanho="12sp", altura=dp(18)))
    barra.add_widget(marca)
    return barra


def pagina():
    """Fundo creme padrão para o corpo de cada tela."""
    raiz = BoxLayout(orientation="vertical")
    pintar_fundo(raiz, CORES["fundo"], raio=0)
    return raiz
