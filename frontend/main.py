"""
main.py (frontend)
------------------
Interface gráfica do app, feita em Kivy. Roda no Windows (vira .exe) e no
Android (vira APK), usando o MESMO código.

Esta versão traz um visual moderno ("como um site", porém nativo): paleta
inspirada no conceito do app — pasto (verde), leite (creme/branco), terra de
curral (marrom) e um botão de gravação em terracota. Todos os componentes são
desenhados com cantos arredondados sobre a tela (canvas), formando cartões,
botões "pill", campos com contorno suave e chips de status.

A LÓGICA é idêntica à versão anterior: mesmas telas, mesmos campos e as mesmas
chamadas ao backend (database, audio_processor, ai_analyzer, google_sheets_sync).

Como rodar no computador (modo teste):
    pip install kivy SpeechRecognition
    python -m frontend.main

Telas:
    1. Inicial       -> nome da fazenda + do veterinário, status online, sincronizar
    2. Atendimento   -> id da vaca, botão gravar, campos preenchidos pela IA, salvar
    3. Histórico     -> últimos atendimentos, filtro por vaca
    4. Configurações -> informações e ajuda
"""

import os
import shutil
from datetime import datetime

from kivy.config import Config
# Desliga a simulação de multitouch do mouse (botão direito deixava uma
# bolinha vermelha permanente na tela). Precisa vir antes do Window existir.
Config.set("input", "mouse", "mouse,disable_multitouch")

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp

from backend import database, audio_processor, ai_analyzer, google_sheets_sync
from backend import config, google_auth
from backend.models import Atendimento
from backend.config import COLUNAS_EXIBICAO


# Guarda dados da sessão atual (fazenda e tipo de produção) para não repetir
SESSAO = {"propriedade": "", "tipo_producao": config.TIPO_PRODUCAO_OPCOES[1],  # "Leite"
          "usuario": "", "nuvem": False}


# ===========================================================================
# FONTE DE ÍCONES — Material Design Icons (evita "tofu"/quadrado indefinido
# que aparecia com emojis, pois a fonte padrão do Kivy/Roboto não tem esses
# glifos). Um único .ttf, idêntico no Windows e no Android.
# ===========================================================================
_PASTA_FONTES = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "assets", "fonts")
_ARQUIVO_MDI = os.path.join(_PASTA_FONTES, "materialdesignicons-webfont.ttf")

FONTE_ICONES = "Icones"
if os.path.isfile(_ARQUIVO_MDI):
    LabelBase.register(name=FONTE_ICONES, fn_regular=_ARQUIVO_MDI)
else:
    FONTE_ICONES = None  # se o .ttf não existir, cai no texto normal sem quebrar

# Nome amigável -> ponto de código do glifo na fonte MDI
ICONES = {
    "vaca": "\U000F019A",
    "estetoscopio": "\U000F04D9",
    "prancheta": "\U000F014D",
    "nuvem_subir": "\U000F0167",
    "engrenagem": "\U000F0493",
    "microfone": "\U000F036C",
    "fone": "\U000F02CB",
    "salvar": "\U000F0193",
    "lupa": "\U000F0349",
    "estrelas": "\U000F0674",
    "check_circulo": "\U000F05E0",
    "relogio": "\U000F0150",
    "lampada": "\U000F06E8",
    "voltar": "\U000F0141",
    "lixeira": "\U000F01B4",
}


def icone(nome, tamanho="20sp", cor=(1, 1, 1, 1)):
    """Cria um Label com um glifo da fonte de ícones (ou texto de reserva)."""
    glifo = ICONES.get(nome, "?")
    kwargs = dict(text=glifo, font_size=tamanho, color=cor,
                  size_hint=(None, None))
    if FONTE_ICONES:
        kwargs["font_name"] = FONTE_ICONES
    lbl = Label(**kwargs)
    lbl.texture_update()
    lbl.size = lbl.texture_size
    return lbl


def rotulo_icone(nome, texto):
    """Monta 'texto de markup' combinando um glifo da fonte de ícones com
    texto normal no MESMO Label (usado em botões e títulos)."""
    glifo = ICONES.get(nome, "?")
    if FONTE_ICONES:
        return "[font=%s]%s[/font]  %s" % (FONTE_ICONES, glifo, texto)
    return texto  # fonte indisponível: mostra só o texto, sem quadradinho


# ===========================================================================
# IDENTIDADE VISUAL — cores inspiradas no conceito (pasto, leite, curral)
# ===========================================================================
PALETA_CLARA = {
    "fundo":        (0.960, 0.949, 0.921, 1),  # F5F2EB  creme (leite/palha)
    "verde":        (0.176, 0.482, 0.353, 1),  # 2D7B5A  pasto
    "verde_claro":  (0.298, 0.686, 0.490, 1),  # 4CAF7D  broto
    "verde_escuro": (0.098, 0.322, 0.239, 1),  # 19523D  mata fechada
    "terracota":    (0.878, 0.353, 0.196, 1),  # E05A32  gravar (terra/alerta)
    "azul":         (0.180, 0.435, 0.596, 1),  # 2E6F98  nuvem/sincronizar
    "marrom":       (0.451, 0.361, 0.290, 1),  # 735C4A  couro/curral
    "cartao":       (1, 1, 1, 1),              # branco  leite
    "texto":        (0.157, 0.196, 0.180, 1),  # 28322E  escuro esverdeado
    "texto_suave":  (0.435, 0.463, 0.451, 1),  # 6F7673  cinza
    "texto_campo":  (0.098, 0.322, 0.239, 1),  # verde escuro (texto ao digitar)
    "borda":        (0.878, 0.867, 0.831, 1),  # E0DDD4  contorno suave
    "chip_ok":      (0.851, 0.933, 0.882, 1),  # verde bem claro (sincronizado)
    "chip_pend":    (0.996, 0.925, 0.804, 1),  # âmbar claro (pendente)
    "amarelo":      (0.945, 0.749, 0.259, 1),  # F0BF42  destaque
}

# Tema escuro DE VERDADE: fundo, cartões E campos de texto ficam escuros; o
# texto passa a ser claro. Antes os cartões continuavam brancos (ficavam
# "quadrados brancos" no escuro) — agora tudo escurece de forma consistente.
PALETA_ESCURA = {
    "fundo":        (0.071, 0.086, 0.078, 1),  # quase preto esverdeado
    "verde":        (0.239, 0.573, 0.427, 1),  # mais vibrante p/ contraste no escuro
    "verde_claro":  (0.353, 0.749, 0.541, 1),
    "verde_escuro": (0.156, 0.427, 0.318, 1),
    "terracota":    (0.937, 0.427, 0.267, 1),
    "azul":         (0.341, 0.612, 0.780, 1),
    "marrom":       (0.596, 0.494, 0.408, 1),
    "cartao":       (0.129, 0.149, 0.141, 1),  # cinza-esverdeado escuro (card)
    "texto":        (0.902, 0.918, 0.910, 1),  # quase branco
    "texto_suave":  (0.639, 0.667, 0.651, 1),  # cinza claro
    "texto_campo":  (0.902, 0.918, 0.910, 1),  # texto claro ao digitar no escuro
    "borda":        (0.243, 0.271, 0.255, 1),  # contorno escuro sutil
    # badges continuam claros (pílulas pequenas legíveis sobre o card escuro)
    "chip_ok":      (0.851, 0.933, 0.882, 1),
    "chip_pend":    (0.996, 0.925, 0.804, 1),
    "amarelo":      (0.976, 0.804, 0.333, 1),
}

CORES = dict(PALETA_CLARA)  # dict MUTÁVEL — trocamos os valores ao mudar de tema
TEMA = {"escuro": False}


def _arquivo_preferencias():
    from backend.config import DATA_DIR
    return os.path.join(DATA_DIR, "preferencias.json")


def _carregar_tema_salvo():
    import json
    try:
        with open(_arquivo_preferencias(), "r", encoding="utf-8") as f:
            return bool(json.load(f).get("tema_escuro", False))
    except (FileNotFoundError, ValueError, OSError):
        return False


def aplicar_tema(escuro: bool, salvar: bool = True):
    """Troca a paleta ativa (CORES) e persiste a escolha em disco."""
    TEMA["escuro"] = escuro
    CORES.clear()
    CORES.update(PALETA_ESCURA if escuro else PALETA_CLARA)
    if Window is not None:
        Window.clearcolor = CORES["fundo"]
    if salvar:
        import json
        try:
            with open(_arquivo_preferencias(), "w", encoding="utf-8") as f:
                json.dump({"tema_escuro": escuro}, f)
        except OSError:
            pass  # não é crítico se não conseguir salvar a preferência


TEMA["escuro"] = _carregar_tema_salvo()
if TEMA["escuro"]:
    CORES.clear()
    CORES.update(PALETA_ESCURA)


def _escurecer(cor, f=0.82):
    r, g, b, a = cor
    return (r * f, g * f, b * f, a)


def _pintar_fundo(widget, cor, raio=14, borda=None, largura=1.2):
    """Desenha um retângulo arredondado atrás de qualquer widget.

    IMPORTANTE: as instruções de Color ficam "ativas" (tingem o que for
    desenhado a seguir) até a PRÓXIMA Color, mesmo atravessando de
    canvas.before para o canvas do próprio widget — não são isoladas por
    canvas. Sem resetar para branco no final, a última cor usada aqui
    (ex.: a cor da borda) "vazava" e tingia o TEXTO desenhado depois pelo
    próprio widget (foi exatamente o bug que deixava letras pretas
    aparecendo verdes: a borda do campo em foco pintava o texto por cima).
    """
    with widget.canvas.before:
        widget._cor_inst = Color(*cor)
        widget._rect_inst = RoundedRectangle(radius=[raio])
        if borda is not None:
            widget._cor_borda = Color(*borda)
            widget._linha_inst = Line(width=largura)
        Color(1, 1, 1, 1)  # reseta para branco neutro antes do widget desenhar

    def _atualizar(*_):
        widget._rect_inst.pos = widget.pos
        widget._rect_inst.size = widget.size
        if borda is not None:
            x, y = widget.pos
            w, h = widget.size
            widget._linha_inst.rounded_rectangle = (x, y, w, h, raio)

    widget.bind(pos=_atualizar, size=_atualizar)
    _atualizar()
    return widget


# ===========================================================================
# COMPONENTES DE INTERFACE (cartões, botões, campos, chips)
# ===========================================================================
class Cartao(BoxLayout):
    """Uma "caixa" branca arredondada, como um card de site.

    IMPORTANTE: dentro de um ScrollView, todo filho precisa ter altura
    definida (size_hint_y=None). Por padrão, o cartão se ajusta à altura do
    próprio conteúdo; se o chamador passar uma 'height' fixa, ela é respeitada.
    """
    def __init__(self, cor=None, raio=18, borda=True, **kwargs):
        altura_fixa = "height" in kwargs
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(16))
        kwargs.setdefault("spacing", dp(10))
        super().__init__(**kwargs)
        _pintar_fundo(self, cor or CORES["cartao"], raio,
                      borda=CORES["borda"] if borda else None)
        # Sem altura fixa -> encolhe/cresce conforme o conteúdo (não colapsa a 0).
        if not altura_fixa:
            self.size_hint_y = None
            self.bind(minimum_height=self.setter("height"))


class CartaoClicavel(ButtonBehavior, Cartao):
    """Um Cartao que responde a toque — usado nos cards do histórico, que
    abrem um popup com o histórico completo daquela vaca ao serem tocados."""
    def on_press(self):
        if hasattr(self, "_cor_inst"):
            self._cor_antes_do_toque = tuple(self._cor_inst.rgba)
            self._cor_inst.rgba = _escurecer(self._cor_antes_do_toque, 0.95)

    def on_release(self):
        if hasattr(self, "_cor_antes_do_toque"):
            self._cor_inst.rgba = self._cor_antes_do_toque


class Botao(ButtonBehavior, Label):
    """Botão "pill" totalmente estilizado (cor, cantos, feedback ao toque).

    IMPORTANTE: este widget já desenha o próprio fundo em canvas.before.
    Nunca chame _pintar_fundo() sobre um Botao — isso desenharia um segundo
    retângulo POR CIMA do primeiro, sempre com a cor inicial (estática), e
    esconderia qualquer mudança de cor feita depois (foi exatamente o bug
    que deixava o texto branco "sumindo" num fundo branco ao selecionar uma
    opção). Se precisar de contorno, use o parâmetro `borda` abaixo.
    """
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
        self._c.rgba = _escurecer(self._cor)

    def on_release(self):
        self._c.rgba = self._cor

    def piscar(self, cor_flash=(1, 1, 1, 0.55), duracao=0.12):
        """Pisca um brilho rápido — feedback visual de 'toque registrado',
        usado quando o usuário seleciona uma opção (chip/segmented control).
        """
        from kivy.animation import Animation
        original = self._c.rgba
        self._c.rgba = cor_flash
        Animation(rgba=original, duration=duracao, t="out_quad").start(self._c)


class Campo(TextInput):
    """Campo de texto com fundo branco e contorno suave.

    Texto em verde-escuro (cor da marca) e cursor piscante ao ganhar foco.

    IMPORTANTE: usamos o FUNDO NATIVO do TextInput (background_color +
    background_normal/active), e NÃO o _pintar_fundo() com canvas.before.
    O _pintar_fundo mexe no estado de Color do canvas e, no TextInput,
    isso fazia o texto e o cursor sumirem (as letras eram digitadas e
    guardadas normalmente, mas não eram desenhadas na tela). O fundo
    nativo renderiza o texto de forma confiável.
    """
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
    """ScrollView que dá foco IMEDIATO a um campo de texto ao ser tocado.

    Por padrão o ScrollView segura o toque por alguns milissegundos para
    decidir se é rolagem e só então repassa ao filho. No Android isso fazia o
    teclado abrir apenas enquanto o dedo ficava pressionado (e sumir ao
    soltar). Aqui, ao tocar sobre um campo, focamos na hora — o teclado abre
    no primeiro toque e continua aberto depois de soltar o dedo.
    """
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._focar_campo_sob_toque(self, touch.pos[0], touch.pos[1])
        return super().on_touch_down(touch)

    def _focar_campo_sob_toque(self, widget, tx, ty):
        # Procura de cima para baixo o campo de texto sob o toque e o foca.
        # Usa coordenadas ABSOLUTAS de janela (to_window) para funcionar mesmo
        # com o conteúdo rolado.
        for filho in widget.children:
            if self._focar_campo_sob_toque(filho, tx, ty):
                return True
        if isinstance(widget, TextInput) and not widget.disabled:
            wx, wy = widget.to_window(widget.x, widget.y)
            if wx <= tx <= wx + widget.width and wy <= ty <= wy + widget.height:
                widget.focus = True
                return True
        return False


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
    _pintar_fundo(caixa, cor_fundo, raio=13)
    if icone_nome:
        ic = icone(icone_nome, tamanho="13sp", cor=cor_texto)
        # Sem isto o ícone (size_hint_y=None) encostava embaixo, ficando mais
        # baixo que o texto. center_y=0.5 alinha o símbolo ao centro do chip.
        ic.pos_hint = {"center_y": 0.5}
        caixa.add_widget(ic)
    lbl = Label(text=texto, markup=True, color=cor_texto, font_size="12sp",
                bold=True)
    caixa.add_widget(lbl)
    return caixa


class SeletorOpcoes(GridLayout):
    """"Segmented control" — linha (ou grade) de botões onde só uma opção
    fica destacada por vez. Usado para Corte/Leite, Prenha/Vazia e
    Diagnóstico, no lugar de o veterinário ter que digitar tudo à mão.
    """
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
            botao.piscar()  # feedback visual de que o toque foi registrado
        if disparar_callback and self._ao_selecionar:
            self._ao_selecionar(opcao)

    def _atualizar_destaque(self):
        for opcao, botao in self._botoes.items():
            ativo = (opcao == self._valor)
            cor = CORES["verde"] if ativo else CORES["cartao"]
            botao._cor = cor
            botao._c.rgba = cor
            botao.color = (1, 1, 1, 1) if ativo else CORES["texto_suave"]


def _ir_inicial(*_):
    App.get_running_app().root.current = "inicial"


def cabecalho(titulo, subtitulo="", icone_nome="vaca", com_voltar=False):
    """Barra superior verde com marca do app e (opcional) botão de voltar."""
    barra = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(78),
                      padding=[dp(14), dp(10)], spacing=dp(10))
    _pintar_fundo(barra, CORES["verde"], raio=0)

    if com_voltar:
        voltar = Botao(texto=rotulo_icone("voltar", ""), cor=CORES["verde_escuro"],
                       raio=14, size_hint=(None, 1), width=dp(46), font_size="22sp")
        voltar.bind(on_release=_ir_inicial)
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
    _pintar_fundo(raiz, CORES["fundo"], raio=0)
    return raiz


def aviso(titulo, mensagem):
    """Janelinha de aviso estilizada."""
    conteudo = Cartao(padding=dp(18), spacing=dp(14))
    conteudo.add_widget(texto_livre("[b]%s[/b]" % titulo, cor=CORES["verde"],
                                    tamanho="17sp", altura=dp(26)))
    corpo = texto_livre(mensagem, cor=CORES["texto"], tamanho="14sp")
    corpo.valign = "top"
    conteudo.add_widget(corpo)
    botao = Botao(texto="OK", cor=CORES["verde"], size_hint_y=None, height=dp(46))
    conteudo.add_widget(botao)
    popup = Popup(title="", separator_height=0, content=conteudo,
                  size_hint=(0.86, 0.42),
                  background="", background_color=(0, 0, 0, 0.45))
    botao.bind(on_release=popup.dismiss)
    popup.open()


def confirmar(titulo, mensagem, ao_confirmar, texto_confirmar="Excluir"):
    """Janelinha de confirmação com dois botões: Cancelar e uma ação
    destrutiva (vermelho). Só chama `ao_confirmar` se o usuário confirmar."""
    conteudo = Cartao(padding=dp(18), spacing=dp(14))
    conteudo.add_widget(texto_livre("[b]%s[/b]" % titulo, cor=CORES["terracota"],
                                    tamanho="17sp", altura=dp(26)))
    corpo = texto_livre(mensagem, cor=CORES["texto"], tamanho="14sp")
    corpo.valign = "top"
    conteudo.add_widget(corpo)

    linha = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(12))
    botao_cancelar = Botao(texto="Cancelar", cor=CORES["cartao"],
                           cor_texto=CORES["texto_suave"], borda=CORES["borda"])
    botao_excluir = Botao(texto=rotulo_icone("lixeira", texto_confirmar),
                          cor=CORES["terracota"])
    linha.add_widget(botao_cancelar)
    linha.add_widget(botao_excluir)
    conteudo.add_widget(linha)

    popup = Popup(title="", separator_height=0, content=conteudo,
                  size_hint=(0.86, 0.42),
                  background="", background_color=(0, 0, 0, 0.45))
    botao_cancelar.bind(on_release=popup.dismiss)

    def _confirmar(*_):
        popup.dismiss()
        ao_confirmar()
    botao_excluir.bind(on_release=_confirmar)
    popup.open()


def alternar_gravacao(host, botao, campo, rotulo_idle="GRAVAR E FALAR",
                      ao_final=None):
    """Liga/desliga a captação de voz AO VIVO.

    - 1º toque: começa a ouvir; a transcrição vai aparecendo no `campo`
      enquanto a pessoa fala (resultados parciais).
    - 2º toque (ou fim automático): para a captação.

    Guarda a sessão em host._sessao_audio para saber se está ouvindo. É usado
    tanto na "nota rápida" (tela inicial) quanto no atendimento.
    """
    sessao = getattr(host, "_sessao_audio", None)
    if sessao is not None:
        # Já está ouvindo: este toque é o "Parar".
        try:
            sessao.parar()
        except Exception:
            pass
        return

    def _repor_botao(*_):
        botao.text = rotulo_icone("microfone", rotulo_idle)
        botao._cor = CORES["terracota"]
        botao._c.rgba = CORES["terracota"]

    def on_parcial(texto):
        Clock.schedule_once(lambda *_: setattr(campo, "text", texto))

    def on_final(texto):
        texto = (texto or "").strip()
        if texto:
            texto = ai_analyzer.corrigir_transcricao(texto)

        def _ui(*_):
            host._sessao_audio = None
            _repor_botao()
            if texto:
                campo.text = texto
                if ao_final:
                    ao_final(texto)
        Clock.schedule_once(_ui)

    def on_erro(codigo):
        def _ui(*_):
            host._sessao_audio = None
            _repor_botao()
            aviso("Áudio", audio_processor.mensagem_erro_audio(codigo))
        Clock.schedule_once(_ui)

    try:
        host._sessao_audio = audio_processor.iniciar_transcricao_ao_vivo(
            callback_parcial=on_parcial, callback_final=on_final,
            callback_erro=on_erro)
    except Exception as erro:
        host._sessao_audio = None
        aviso("Áudio", "Não foi possível iniciar a captação de voz. Você "
              "pode digitar o texto manualmente.\n\n(%s)" % erro)
        return

    campo.text = ""
    botao.text = rotulo_icone("fone", "OUVINDO — TOQUE PARA PARAR")
    botao._cor = CORES["verde"]
    botao._c.rgba = CORES["verde"]


# ===========================================================================
# TELA 0 — ABERTURA (splash) — símbolo da marca + nome do app por ~1,4s
# ===========================================================================
class TelaSplash(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical")
        _pintar_fundo(raiz, CORES["verde"], raio=0)

        raiz.add_widget(Widget())  # espaçador flexível — empurra o conteúdo pro centro

        simbolo = Label(text=ICONES.get("vaca", "?"), font_size="92sp",
                        color=(1, 1, 1, 1), size_hint_y=None, height=dp(110),
                        halign="center", valign="middle")
        if FONTE_ICONES:
            simbolo.font_name = FONTE_ICONES
        simbolo.bind(size=simbolo.setter("text_size"))
        raiz.add_widget(simbolo)

        nome = Label(text="[b]VacaVet[/b]", markup=True, font_size="32sp",
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

        raiz.add_widget(Widget())  # espaçador flexível — mantém tudo centralizado

        self.add_widget(raiz)
        self._evento_transicao = None

    def on_enter(self):
        # Abre por 2 segundos e então vai para a tela de login/cadastro.
        self._evento_transicao = Clock.schedule_once(self._ir_para_login, 2.0)

    def on_leave(self):
        if self._evento_transicao:
            self._evento_transicao.cancel()

    def _ir_para_login(self, *_):
        if self.manager:
            # Se já estiver logado nesta sessão, pula direto para o app.
            self.manager.current = "inicial" if SESSAO.get("usuario") else "login"


# ===========================================================================
# TELA 0.5 — LOGIN / CADASTRO (beta)
# ===========================================================================
class TelaLogin(Screen):
    """Depois da abertura, o nome e a logo ficam no TERÇO SUPERIOR (faixa verde)
    e abaixo aparece o login/cadastro. Como está em BETA, é uma entrada
    simples: um nome + 'Entrar', ou 'Entrar com Google' (nuvem)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical")
        _pintar_fundo(raiz, CORES["fundo"], raio=0)

        # --- Terço superior: faixa verde com logo + nome ---
        topo = BoxLayout(orientation="vertical", size_hint_y=0.34,
                         padding=dp(16), spacing=dp(4))
        _pintar_fundo(topo, CORES["verde"], raio=0)
        topo.add_widget(Widget())
        simbolo = Label(text=ICONES.get("vaca", "?"), font_size="64sp",
                        color=(1, 1, 1, 1), size_hint_y=None, height=dp(78),
                        halign="center", valign="middle")
        if FONTE_ICONES:
            simbolo.font_name = FONTE_ICONES
        simbolo.bind(size=simbolo.setter("text_size"))
        topo.add_widget(simbolo)
        nome = Label(text="[b]VacaVet[/b]", markup=True, font_size="30sp",
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

        meio.add_widget(cartao)
        meio.add_widget(Widget())
        raiz.add_widget(meio)
        self.add_widget(raiz)

    def _entrar(self, *_):
        nome = self.campo_nome.text.strip()
        if not nome:
            aviso("Atenção", "Escreva seu nome para entrar (versão beta).")
            return
        SESSAO["usuario"] = nome
        SESSAO["nuvem"] = False
        self.manager.current = "inicial"

    def _entrar_google(self, *_):
        """Login REAL com Google (OAuth). Abre o navegador na tela de
        consentimento; ao voltar, o app fica conectado e passa a criar/atualizar
        a planilha no Drive do próprio usuário ao sincronizar."""
        # Se já está logado neste aparelho, entra direto.
        if google_auth.esta_logado():
            SESSAO["usuario"] = google_auth.email_logado() or "Conta Google"
            SESSAO["nuvem"] = True
            self.manager.current = "inicial"
            return

        if not google_auth.esta_configurado():
            aviso("Login com Google",
                  "O login com Google ainda não está configurado neste app "
                  "(faltam as credenciais OAuth). Enquanto isso, você pode usar "
                  "o app normalmente e sincronizar em modo local.")
            return

        aviso("Login com Google",
              "Vou abrir o navegador para você entrar na sua conta Google e "
              "autorizar. Depois de autorizar, volte para o VacaVet.")

        def ao_sucesso(email):
            def _ui(*_):
                SESSAO["usuario"] = email or "Conta Google"
                SESSAO["nuvem"] = True
                aviso("Conectado ao Google",
                      "Login concluído como:\n%s\n\nAgora o botão Sincronizar "
                      "cria/atualiza a planilha no seu Drive." % (email or "—"))
                self.manager.current = "inicial"
            Clock.schedule_once(_ui)

        def ao_erro(msg):
            Clock.schedule_once(lambda *_: aviso(
                "Login com Google", "Não foi possível concluir o login.\n\n%s"
                % msg))

        google_auth.login(callback_sucesso=ao_sucesso, callback_erro=ao_erro)


# ===========================================================================
# TELA 1 — INICIAL
# ===========================================================================
class TelaInicial(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(cabecalho("VacaVet", "Atendimento por voz no curral",
                                  icone_nome="vaca"))

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(16),
                          size_hint_y=None)
        corpo.bind(minimum_height=corpo.setter("height"))

        # --- Cartão: boas-vindas ---
        boas = Cartao()
        boas.add_widget(texto_livre("[b]Bem-vindo(a)![/b]", cor=CORES["texto"],
                                    tamanho="18sp", altura=dp(26)))
        corpo.add_widget(boas)

        # --- Cartão: nota rápida por voz (grava e transcreve o que fazer) ---
        nota = Cartao()
        nota.add_widget(texto_livre("[b]Nota rápida por voz[/b]",
                                    cor=CORES["verde"], tamanho="15sp",
                                    altura=dp(24)))
        nota.add_widget(texto_livre(
            "Grave um lembrete do que precisa ser feito — ele é transcrito aqui.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(34)))
        self.botao_gravar_nota = Botao(
            texto=rotulo_icone("microfone", "GRAVAR E FALAR"),
            cor=CORES["terracota"], size_hint_y=None, height=dp(60),
            font_size="17sp")
        self.botao_gravar_nota.bind(on_release=self.gravar_nota)
        nota.add_widget(self.botao_gravar_nota)
        self.nota_transcricao = Campo(
            hint_text="A fala aparece aqui — ou digite um lembrete",
            size_hint_y=None, height=dp(74))
        nota.add_widget(self.nota_transcricao)
        corpo.add_widget(nota)

        # --- Cartão: dados da sessão ---
        dados = Cartao()
        dados.add_widget(texto_livre("[b]Dados da jornada[/b]", cor=CORES["verde"],
                                     tamanho="15sp", altura=dp(24)))

        dados.add_widget(etiqueta("Propriedade / Fazenda"))
        # Linha: campo de texto + botão "Adicionar propriedade" ao lado.
        linha_prop = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.campo_propriedade = Campo(multiline=False, hint_text="Ex: Fazenda Boa Vista")
        self.seletor_propriedades = None  # criado dinamicamente conforme o banco
        self.campo_propriedade.bind(text=self._ao_editar_propriedade_manual)
        botao_add_prop = Botao(texto=rotulo_icone("salvar", "Adicionar"),
                               cor=CORES["verde_claro"], size_hint_x=None,
                               width=dp(128), font_size="13sp")
        botao_add_prop.bind(on_release=lambda *_: self._adicionar_propriedade())
        linha_prop.add_widget(self.campo_propriedade)
        linha_prop.add_widget(botao_add_prop)
        dados.add_widget(linha_prop)

        # Propriedades já usadas antes aparecem como atalhos — toca e reaproveita.
        # Para cadastrar uma nova, é só digitar um nome diferente no campo acima.
        self.caixa_propriedades_salvas = BoxLayout(orientation="vertical",
                                                    size_hint_y=None, spacing=dp(6))
        self.caixa_propriedades_salvas.bind(
            minimum_height=self.caixa_propriedades_salvas.setter("height"))
        dados.add_widget(self.caixa_propriedades_salvas)

        dados.add_widget(etiqueta("Tipo de Produção"))
        self.seletor_tipo = SeletorOpcoes(config.TIPO_PRODUCAO_OPCOES,
                                          valor_inicial=SESSAO["tipo_producao"])
        dados.add_widget(self.seletor_tipo)
        corpo.add_widget(dados)

        # --- Chip de status de sincronização ---
        self.caixa_status = BoxLayout(size_hint_y=None, height=dp(30),
                                      spacing=dp(8))
        corpo.add_widget(self.caixa_status)

        # --- Ações principais ---
        botao_iniciar = Botao(texto=rotulo_icone("estetoscopio", "Iniciar Atendimento"),
                              cor=CORES["verde"],
                              size_hint_y=None, height=dp(58), font_size="17sp")
        botao_iniciar.bind(on_release=self.iniciar)
        corpo.add_widget(botao_iniciar)

        linha = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))
        botao_historico = Botao(texto=rotulo_icone("prancheta", "Histórico"),
                                cor=CORES["marrom"])
        botao_historico.bind(on_release=lambda *_: self.ir("historico"))
        botao_sincronizar = Botao(texto=rotulo_icone("nuvem_subir", "Sincronizar"),
                                  cor=CORES["azul"])
        botao_sincronizar.bind(on_release=self.sincronizar)
        linha.add_widget(botao_historico)
        linha.add_widget(botao_sincronizar)
        corpo.add_widget(linha)

        botao_config = Botao(texto=rotulo_icone("engrenagem", "Configurações e Ajuda"),
                             cor=CORES["cartao"], cor_texto=CORES["texto_suave"],
                             borda=CORES["borda"], size_hint_y=None, height=dp(48))
        botao_config.bind(on_release=lambda *_: self.ir("config"))
        corpo.add_widget(botao_config)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def on_pre_enter(self):
        self.campo_propriedade.text = SESSAO["propriedade"]
        self.seletor_tipo.selecionar(SESSAO["tipo_producao"], disparar_callback=False)
        self._atualizar_propriedades_salvas()
        pendentes = len(database.listar_nao_sincronizados())
        self.caixa_status.clear_widgets()
        self.caixa_status.add_widget(Widget())  # espaçador à esquerda (centraliza)
        if pendentes:
            self.caixa_status.add_widget(
                chip("%d aguardando nuvem" % pendentes,
                     CORES["chip_pend"], CORES["marrom"], icone_nome="relogio"))
        else:
            self.caixa_status.add_widget(
                chip("Tudo sincronizado", CORES["chip_ok"], CORES["verde_escuro"],
                     icone_nome="check_circulo"))
        self.caixa_status.add_widget(Widget())  # espaçador à direita (centraliza)

    def _atualizar_propriedades_salvas(self):
        self.caixa_propriedades_salvas.clear_widgets()
        salvas = database.listar_propriedades()
        if not salvas:
            self.seletor_propriedades = None
            return  # primeira vez usando o app: nada para sugerir ainda
        self.caixa_propriedades_salvas.add_widget(
            etiqueta("Ou toque numa já usada"))
        texto_atual = self.campo_propriedade.text.strip()
        # "Abre" (destaca em verde) a propriedade já usada que bater com o que
        # está escrito no campo agora — mesmo comportamento de seleção do
        # Corte/Leite, para ficar óbvio qual está ativa.
        self.seletor_propriedades = SeletorOpcoes(
            salvas[:8], cols=2, altura_linha=dp(38),
            valor_inicial=texto_atual if texto_atual in salvas else "",
            ao_selecionar=self._escolher_propriedade)
        self.caixa_propriedades_salvas.add_widget(self.seletor_propriedades)

        # Botão para abrir o gerenciador (excluir fazendas que não usa mais)
        botao_gerenciar = Botao(
            texto=rotulo_icone("lixeira", "Gerenciar fazendas"),
            cor=CORES["cartao"], cor_texto=CORES["texto_suave"],
            borda=CORES["borda"], size_hint_y=None, height=dp(38),
            font_size="13sp")
        botao_gerenciar.bind(on_release=lambda *_: self._gerenciar_propriedades())
        self.caixa_propriedades_salvas.add_widget(botao_gerenciar)

    def _gerenciar_propriedades(self):
        """Popup que lista as fazendas salvas com um botão de lixeira em cada
        uma. Excluir uma fazenda apaga TODOS os atendimentos dela."""
        salvas = database.listar_propriedades()
        conteudo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        _pintar_fundo(conteudo, CORES["fundo"], raio=18)
        conteudo.add_widget(texto_livre(
            "[b]Gerenciar fazendas[/b]", cor=CORES["verde"],
            tamanho="16sp", altura=dp(30)))
        conteudo.add_widget(texto_livre(
            "Excluir uma fazenda apaga todos os atendimentos dela.",
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
                      size_hint=(0.9, 0.8), background="",
                      background_color=(0, 0, 0, 0.5))
        botao_fechar.bind(on_release=popup.dismiss)
        # Ao fechar, atualiza os atalhos de fazenda na tela inicial.
        popup.bind(on_dismiss=lambda *_: self._atualizar_propriedades_salvas())

        def recarregar():
            restantes = database.listar_propriedades()
            grade.clear_widgets()
            if not restantes:
                vazio = Cartao(size_hint_y=None, height=dp(64))
                vazio.add_widget(texto_livre(
                    "Nenhuma fazenda salva.", cor=CORES["texto_suave"],
                    tamanho="13sp"))
                grade.add_widget(vazio)
                return
            for nome in restantes:
                grade.add_widget(self._linha_propriedade(nome, recarregar))

        def _construir():
            grade.clear_widgets()
            if not salvas:
                vazio = Cartao(size_hint_y=None, height=dp(64))
                vazio.add_widget(texto_livre(
                    "Nenhuma fazenda salva.", cor=CORES["texto_suave"],
                    tamanho="13sp"))
                grade.add_widget(vazio)
            else:
                for nome in salvas:
                    grade.add_widget(self._linha_propriedade(nome, recarregar))
        _construir()
        popup.open()

    def _linha_propriedade(self, nome, apos_excluir):
        cartao = Cartao(orientation="horizontal", size_hint_y=None, height=dp(56),
                        padding=dp(12), spacing=dp(10))
        rotulo = texto_livre("[b]%s[/b]" % nome, cor=CORES["texto"],
                             tamanho="14sp")
        cartao.add_widget(rotulo)
        botao_lixeira = Botao(texto=rotulo_icone("lixeira", ""),
                              cor=CORES["terracota"], raio=10,
                              size_hint=(None, None), width=dp(48),
                              height=dp(36), font_size="16sp")

        def excluir(*_):
            confirmar(
                "Excluir fazenda",
                "Apagar a fazenda \"%s\" e TODOS os atendimentos dela? "
                "Não dá para desfazer." % nome,
                ao_confirmar=lambda: (
                    database.excluir_propriedade(nome),
                    self._limpar_campo_se_igual(nome), apos_excluir()))
        botao_lixeira.bind(on_release=excluir)
        cartao.add_widget(botao_lixeira)
        return cartao

    def _limpar_campo_se_igual(self, nome):
        """Se a fazenda excluída era a que estava escrita no campo, limpa."""
        if self.campo_propriedade.text.strip() == nome:
            self.campo_propriedade.text = ""

    def gravar_nota(self, *_):
        """Liga/desliga a captação de voz ao vivo do lembrete rápido: o texto
        aparece enquanto se fala; tocar de novo para a captação."""
        alternar_gravacao(self, self.botao_gravar_nota, self.nota_transcricao,
                          rotulo_idle="GRAVAR E FALAR")

    def on_leave(self):
        # Se sair da tela ouvindo, cancela a captação para não ficar pendurada.
        sessao = getattr(self, "_sessao_audio", None)
        if sessao is not None:
            try:
                sessao.cancelar()
            except Exception:
                pass
            self._sessao_audio = None

    def _adicionar_propriedade(self):
        """Cadastra a fazenda escrita no campo como um "quadrado" selecionável
        abaixo (igual aos de Corte/Leite), mesmo antes de ter atendimentos."""
        nome = self.campo_propriedade.text.strip()
        if not nome:
            aviso("Atenção", "Escreva o nome da propriedade antes de adicionar.")
            return
        database.adicionar_propriedade(nome)
        self._atualizar_propriedades_salvas()
        # Já deixa a recém-adicionada selecionada (destacada em verde).
        if self.seletor_propriedades and nome in self.seletor_propriedades._botoes:
            self.seletor_propriedades.selecionar(nome, disparar_callback=False)

    def _escolher_propriedade(self, nome):
        self.campo_propriedade.text = nome

    def _ao_editar_propriedade_manual(self, _widget, texto):
        """Se o usuário digitar algo diferente (criando uma propriedade
        nova), tira o destaque de qualquer chip salvo selecionado antes."""
        seletor = getattr(self, "seletor_propriedades", None)
        if seletor is None:
            return
        texto = texto.strip()
        if texto in seletor._botoes and seletor.valor != texto:
            seletor.selecionar(texto, disparar_callback=False)
        elif texto not in seletor._botoes and seletor.valor != "":
            seletor.selecionar("", disparar_callback=False)

    def iniciar(self, *_):
        if not self.campo_propriedade.text.strip():
            aviso("Atenção", "Informe o nome da propriedade para começar.")
            return
        SESSAO["propriedade"] = self.campo_propriedade.text.strip()
        SESSAO["tipo_producao"] = self.seletor_tipo.valor
        self.ir("atendimento")

    def sincronizar(self, *_):
        resultado = google_sheets_sync.sincronizar(
            self.campo_propriedade.text.strip() or "SemNome"
        )
        if resultado.get("modo") == "simulado":
            aviso("Sincronização (modo local)",
                  "Marquei %s atendimento(s) como sincronizados neste "
                  "aparelho.\n\nPara enviar de verdade a uma planilha no seu "
                  "Google Drive, entre com o Google (tela de login)."
                  % resultado["enviados"])
        elif resultado.get("erros"):
            aviso("Sincronização",
                  "Não consegui enviar agora.\n\n%s"
                  % resultado.get("detalhe", "Tente novamente."))
        else:
            corpo = ("Enviados: %s\nErros: %s" %
                     (resultado["enviados"], resultado["erros"]))
            if resultado.get("link"):
                corpo += "\n\nPlanilha no seu Drive:\n%s" % resultado["link"]
            aviso("Sincronizado com o Google", corpo)
        self.on_pre_enter()

    def ir(self, destino):
        self.manager.current = destino


# ===========================================================================
# TELA 2 — ATENDIMENTO
# ===========================================================================
class TelaAtendimento(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(cabecalho("Novo Atendimento", "Fale ou digite os dados",
                                  icone_nome="estetoscopio", com_voltar=True))

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(14),
                          size_hint_y=None)
        corpo.bind(minimum_height=corpo.setter("height"))

        # --- Cartão: identificação da vaca + gravação ---
        topo = Cartao()
        topo.add_widget(etiqueta("Vaca (brinco)"))
        self.campo_id = Campo(multiline=False, hint_text="Ex: 123",
                              size_hint_y=None, height=dp(48), font_size="17sp")
        topo.add_widget(self.campo_id)

        self.botao_gravar = Botao(texto=rotulo_icone("microfone", "GRAVAR E FALAR"),
                                  cor=CORES["terracota"],
                                  size_hint_y=None, height=dp(64), font_size="18sp")
        self.botao_gravar.bind(on_release=self.gravar)
        topo.add_widget(self.botao_gravar)

        topo.add_widget(etiqueta("Transcrição (fala ou digitação)"))
        self.transcricao = Campo(hint_text="A fala aparece aqui — ou digite para testar",
                                 size_hint_y=None, height=dp(74))
        topo.add_widget(self.transcricao)

        botao_analisar = Botao(texto=rotulo_icone("estrelas",
                                                   "Preencher campos a partir da fala"),
                               cor=CORES["verde_claro"], size_hint_y=None,
                               height=dp(48), font_size="15sp")
        botao_analisar.bind(on_release=self.analisar_texto)
        topo.add_widget(botao_analisar)
        corpo.add_widget(topo)

        # --- Cartão: campos do atendimento ---
        ficha = Cartao()
        ficha.add_widget(texto_livre("[b]Ficha do atendimento[/b]",
                                     cor=CORES["verde"], tamanho="15sp",
                                     altura=dp(24)))
        self.campos = {}
        multilinha = ("diagnostico", "observacoes")
        for chave in ["procedimento", "raca", "peso_kg", "idade_anos",
                      "status_reprodutivo", "diagnostico", "medicacoes",
                      "proxima_acao", "observacoes"]:
            ficha.add_widget(etiqueta(COLUNAS_EXIBICAO[chave]))

            if chave == "status_reprodutivo":
                # Status reprodutivo agora é só uma escolha entre Prenha/Vazia
                # (nada de digitar) — o valor fica guardado num Campo "oculto"
                # (existe, mas não é adicionado à tela) para não mexer no
                # resto da lógica de salvar/analisar, que já lê .text.
                entrada = Campo()  # guarda apenas o valor selecionado
                # 'e=entrada' fixa o campo CERTO no callback. Sem isso, a
                # closure capturava a variável 'entrada' do loop, que no fim
                # apontava para o ÚLTIMO campo (observações) — era o bug de
                # "clicar no status/diagnóstico e cair em observações".
                self.seletor_status = SeletorOpcoes(
                    config.STATUS_REPRODUTIVO_OPCOES,
                    ao_selecionar=lambda v, e=entrada: setattr(e, "text", v))
                ficha.add_widget(self.seletor_status)

            elif chave == "diagnostico":
                # Diagnóstico ganha atalhos (chips) para os casos mais comuns,
                # mas continua editável em texto livre para detalhar o caso.
                entrada = Campo(multiline=True, size_hint_y=None, height=dp(64))
                self.seletor_diagnostico = SeletorOpcoes(
                    config.DIAGNOSTICO_OPCOES, cols=2,
                    ao_selecionar=lambda v, e=entrada: setattr(e, "text", v))
                ficha.add_widget(self.seletor_diagnostico)
                ficha.add_widget(entrada)

            else:
                entrada = Campo(multiline=(chave in multilinha), size_hint_y=None,
                                height=dp(64) if chave in multilinha else dp(44))
                ficha.add_widget(entrada)

            self.campos[chave] = entrada
        corpo.add_widget(ficha)

        # --- Ações inferiores ---
        rodape = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(12))
        botao_voltar = Botao(texto="Voltar", cor=CORES["marrom"])
        botao_voltar.bind(on_release=lambda *_: setattr(self.manager,
                                                        "current", "inicial"))
        botao_salvar = Botao(texto=rotulo_icone("salvar", "Salvar"), cor=CORES["verde"])
        botao_salvar.bind(on_release=self.salvar)
        rodape.add_widget(botao_voltar)
        rodape.add_widget(botao_salvar)
        corpo.add_widget(rodape)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def on_pre_enter(self):
        # limpa a tela para um novo atendimento
        self.campo_id.text = ""
        self.transcricao.text = ""
        for entrada in self.campos.values():
            entrada.text = ""
        self.seletor_status.selecionar("", disparar_callback=False)
        self.seletor_diagnostico.selecionar("", disparar_callback=False)

    def gravar(self, *_):
        """Liga/desliga a captação ao vivo do atendimento. Ao terminar,
        preenche os campos automaticamente a partir da fala."""
        alternar_gravacao(self, self.botao_gravar, self.transcricao,
                          rotulo_idle="GRAVAR E FALAR",
                          ao_final=lambda _t: self.analisar_texto())

    def on_leave(self):
        sessao = getattr(self, "_sessao_audio", None)
        if sessao is not None:
            try:
                sessao.cancelar()
            except Exception:
                pass
            self._sessao_audio = None

    def analisar_texto(self, *_):
        texto = self.transcricao.text.strip()
        if not texto:
            aviso("Atenção", "Não há texto para analisar.")
            return
        campos = ai_analyzer.analisar(texto)
        if campos.get("id_vaca") and not self.campo_id.text.strip():
            self.campo_id.text = campos["id_vaca"]
        for chave, entrada in self.campos.items():
            if campos.get(chave):
                entrada.text = campos[chave]
        # Sincroniza o destaque dos seletores com o que a IA sugeriu
        if campos.get("status_reprodutivo"):
            self.seletor_status.selecionar(campos["status_reprodutivo"],
                                           disparar_callback=False)
        if campos.get("diagnostico"):
            self.seletor_diagnostico.selecionar(campos["diagnostico"],
                                                disparar_callback=False)

    def salvar(self, *_):
        if not self.campo_id.text.strip():
            aviso("Atenção", "Informe o número do brinco da vaca.")
            return
        atendimento = Atendimento(
            id_vaca=self.campo_id.text.strip(),
            propriedade=SESSAO["propriedade"],
            tipo_producao=SESSAO["tipo_producao"],
            transcricao_original=self.transcricao.text.strip(),
        )
        for chave, entrada in self.campos.items():
            setattr(atendimento, chave, entrada.text.strip())
        atendimento.preencher_data_hora()
        database.salvar_atendimento(atendimento)
        aviso("Salvo", "Atendimento da vaca %s salvo!\nSerá enviado à nuvem na "
              "próxima sincronização." % atendimento.id_vaca)
        self.on_pre_enter()


# ===========================================================================
# TELA 3 — HISTÓRICO
# ===========================================================================
class TelaHistorico(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(cabecalho("Histórico", "Últimos atendimentos",
                                  icone_nome="prancheta", com_voltar=True))

        corpo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        # --- Seletor de propriedade: as vacas do histórico são mostradas por
        # fazenda (toque numa fazenda para ver só as vacas dela). ---
        self.propriedade_selecionada = ""
        self.caixa_prop_hist = BoxLayout(orientation="vertical", size_hint_y=None,
                                         spacing=dp(6))
        self.caixa_prop_hist.bind(
            minimum_height=self.caixa_prop_hist.setter("height"))
        corpo.add_widget(self.caixa_prop_hist)

        # --- Filtro por nº da vaca ---
        linha_filtro = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.filtro = Campo(hint_text="Filtrar por nº da vaca", multiline=False)
        botao_filtrar = Botao(texto=rotulo_icone("lupa", ""), cor=CORES["verde"],
                              size_hint_x=None, width=dp(60), font_size="18sp")
        botao_filtrar.bind(on_release=lambda *_: self.carregar())
        linha_filtro.add_widget(self.filtro)
        linha_filtro.add_widget(botao_filtrar)
        corpo.add_widget(linha_filtro)

        # --- Lista rolável ---
        scroll = RolagemComCampos()
        self.lista = GridLayout(cols=1, size_hint_y=None, spacing=dp(10),
                                padding=(0, dp(2)))
        self.lista.bind(minimum_height=self.lista.setter("height"))
        scroll.add_widget(self.lista)
        corpo.add_widget(scroll)

        botao_voltar = Botao(texto="Voltar", cor=CORES["marrom"],
                             size_hint_y=None, height=dp(50))
        botao_voltar.bind(on_release=lambda *_: setattr(self.manager,
                                                        "current", "inicial"))
        corpo.add_widget(botao_voltar)

        raiz.add_widget(corpo)
        self.add_widget(raiz)

    def on_pre_enter(self):
        # Por padrão, abre já na fazenda da jornada atual (se houver).
        if not self.propriedade_selecionada:
            self.propriedade_selecionada = SESSAO.get("propriedade", "")
        self._montar_seletor_propriedades()
        self.carregar()

    def _montar_seletor_propriedades(self):
        """Monta os "quadrados" de fazenda no topo (mesmo estilo Corte/Leite).
        Tocar numa fazenda mostra só as vacas dela."""
        self.caixa_prop_hist.clear_widgets()
        propriedades = database.listar_propriedades()
        if not propriedades:
            return
        # Se a fazenda atual não existe mais, cai para a primeira disponível.
        if self.propriedade_selecionada not in propriedades:
            self.propriedade_selecionada = propriedades[0]
        self.caixa_prop_hist.add_widget(etiqueta("Fazenda"))
        self.seletor_prop_hist = SeletorOpcoes(
            propriedades[:8], cols=2, altura_linha=dp(38),
            valor_inicial=self.propriedade_selecionada,
            ao_selecionar=self._trocar_propriedade)
        self.caixa_prop_hist.add_widget(self.seletor_prop_hist)

    def _trocar_propriedade(self, nome):
        self.propriedade_selecionada = nome
        self.carregar()

    def carregar(self):
        """Carrega o histórico da fazenda selecionada, AGRUPADO por vaca: se a
        vaca 123 tem 3 atendimentos, aparece 1 card só (com uma contagem), e
        tocando nele abre a lista completa daquela vaca, do mais recente ao
        mais antigo."""
        self.lista.clear_widgets()
        filtro = self.filtro.text.strip() or None
        atendimentos = database.listar_atendimentos(limite=500, id_vaca=filtro)
        # Filtra pela fazenda selecionada (se houver alguma).
        if self.propriedade_selecionada:
            atendimentos = [a for a in atendimentos
                            if a.propriedade == self.propriedade_selecionada]
        if not atendimentos:
            vazio = Cartao(size_hint_y=None, height=dp(70))
            msg = ("Nenhum atendimento nesta fazenda ainda."
                   if self.propriedade_selecionada
                   else "Nenhum atendimento encontrado.")
            vazio.add_widget(texto_livre(msg, cor=CORES["texto_suave"],
                                         tamanho="14sp"))
            self.lista.add_widget(vazio)
            return

        grupos = {}
        ordem = []
        for a in atendimentos:  # já vem do mais recente para o mais antigo
            if a.id_vaca not in grupos:
                grupos[a.id_vaca] = []
                ordem.append(a.id_vaca)
            grupos[a.id_vaca].append(a)

        for id_vaca in ordem:
            self.lista.add_widget(self._cartao_vaca(id_vaca, grupos[id_vaca]))

    def _cartao_vaca(self, id_vaca, atendimentos):
        mais_recente = atendimentos[0]
        cartao = CartaoClicavel(size_hint_y=None, height=dp(96), padding=dp(14),
                                spacing=dp(6))
        cartao.bind(on_release=lambda *_: self._abrir_historico_vaca(
            id_vaca, atendimentos))

        topo = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        topo.add_widget(texto_livre("[b]%s Vaca %s[/b]" %
                                    (rotulo_icone("vaca", "").rstrip(), id_vaca),
                                    cor=CORES["texto"], tamanho="16sp",
                                    altura=dp(28)))
        topo.add_widget(Widget())
        if len(atendimentos) > 1:
            topo.add_widget(chip("%d registros" % len(atendimentos),
                                 CORES["chip_pend"], CORES["marrom"],
                                 icone_nome="prancheta"))
        elif mais_recente.sincronizado:
            topo.add_widget(chip("nuvem", CORES["chip_ok"], CORES["verde_escuro"],
                                 icone_nome="check_circulo"))
        else:
            topo.add_widget(chip("local", CORES["chip_pend"], CORES["marrom"],
                                 icone_nome="relogio"))
        cartao.add_widget(topo)

        proc = mais_recente.procedimento or "sem procedimento"
        cartao.add_widget(texto_livre("Último: %s" % proc, cor=CORES["verde"],
                                      tamanho="14sp", altura=dp(22), bold=True))

        rodape = "%s %s  ·  %s" % (mais_recente.data, mais_recente.hora,
                                   mais_recente.status_reprodutivo or "sem status")
        cartao.add_widget(texto_livre(rodape, cor=CORES["texto_suave"],
                                      tamanho="12sp", altura=dp(18)))
        return cartao

    def _abrir_historico_vaca(self, id_vaca, atendimentos):
        """Popup com TODOS os atendimentos daquela vaca, do mais recente ao
        mais antigo — é o "abrir e ver tudo que foi feito" pedido."""
        conteudo = BoxLayout(orientation="vertical", padding=dp(16),
                             spacing=dp(12))
        _pintar_fundo(conteudo, CORES["fundo"], raio=18)

        conteudo.add_widget(texto_livre(
            "[b]%s Histórico completo — Vaca %s[/b]" %
            (rotulo_icone("vaca", "").rstrip(), id_vaca),
            cor=CORES["verde"], tamanho="16sp", altura=dp(46)))

        scroll = RolagemComCampos()
        grade = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grade.bind(minimum_height=grade.setter("height"))
        scroll.add_widget(grade)

        popup = Popup(title="", separator_height=0, content=conteudo,
                      size_hint=(0.94, 0.86), background="",
                      background_color=(0, 0, 0, 0.5))

        def recarregar_popup():
            """Depois de excluir um atendimento, atualiza a lista dentro do
            popup. Se a vaca ficou sem nenhum atendimento, fecha o popup e
            recarrega a tela de histórico."""
            restantes = database.listar_atendimentos(limite=200, id_vaca=id_vaca)
            if not restantes:
                popup.dismiss()
                self.carregar()
                return
            grade.clear_widgets()
            for a in restantes:
                grade.add_widget(self._linha_detalhe(a, recarregar_popup))

        for a in atendimentos:
            grade.add_widget(self._linha_detalhe(a, recarregar_popup))
        conteudo.add_widget(scroll)

        # --- Excluir a vaca inteira ---
        def excluir_tudo():
            confirmar(
                "Excluir vaca %s" % id_vaca,
                "Isso apaga TODOS os %d atendimento(s) desta vaca. "
                "Não dá para desfazer." % len(atendimentos),
                ao_confirmar=lambda: (
                    database.excluir_atendimentos_da_vaca(id_vaca),
                    popup.dismiss(), self.carregar()),
                texto_confirmar="Excluir tudo")

        linha_acoes = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(12))
        botao_excluir_vaca = Botao(
            texto=rotulo_icone("lixeira", "Excluir esta vaca"),
            cor=CORES["terracota"])
        botao_excluir_vaca.bind(on_release=lambda *_: excluir_tudo())
        botao_fechar = Botao(texto="Fechar", cor=CORES["marrom"])
        botao_fechar.bind(on_release=popup.dismiss)
        linha_acoes.add_widget(botao_excluir_vaca)
        linha_acoes.add_widget(botao_fechar)
        conteudo.add_widget(linha_acoes)

        popup.open()

    def _linha_detalhe(self, a, apos_excluir=None):
        cartao = Cartao(padding=dp(12), spacing=dp(4))

        marca = "nuvem" if a.sincronizado else "local"
        cor_marca = (CORES["chip_ok"], CORES["verde_escuro"]) if a.sincronizado \
            else (CORES["chip_pend"], CORES["marrom"])
        topo = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        topo.add_widget(texto_livre("[b]%s %s[/b]" % (a.data, a.hora),
                                    cor=CORES["texto"], tamanho="13sp",
                                    altura=dp(28)))
        topo.add_widget(Widget())
        topo.add_widget(chip(marca, cor_marca[0], cor_marca[1]))
        # Botãozinho de lixeira para excluir SÓ este atendimento
        if apos_excluir is not None and a.id_banco is not None:
            botao_lixeira = Botao(texto=rotulo_icone("lixeira", ""),
                                  cor=CORES["terracota"], raio=10,
                                  size_hint=(None, None), width=dp(40),
                                  height=dp(28), font_size="15sp")

            def excluir_este(*_):
                confirmar(
                    "Excluir atendimento",
                    "Apagar este atendimento de %s %s? Não dá para desfazer."
                    % (a.data, a.hora),
                    ao_confirmar=lambda: (
                        database.excluir_atendimento(a.id_banco), apos_excluir()))
            botao_lixeira.bind(on_release=excluir_este)
            topo.add_widget(botao_lixeira)
        cartao.add_widget(topo)

        if a.procedimento:
            cartao.add_widget(texto_livre("[b]Procedimento:[/b] %s" % a.procedimento,
                                          cor=CORES["verde"], tamanho="12sp",
                                          altura=dp(18)))
        if a.status_reprodutivo:
            cartao.add_widget(texto_livre("[b]Status:[/b] %s" % a.status_reprodutivo,
                                          cor=CORES["texto_suave"], tamanho="12sp",
                                          altura=dp(18)))
        if a.diagnostico:
            cartao.add_widget(texto_livre("[b]Diagnóstico:[/b] %s" % a.diagnostico,
                                          cor=CORES["texto_suave"], tamanho="12sp",
                                          altura=dp(18)))
        if a.medicacoes:
            cartao.add_widget(texto_livre("[b]Medicações:[/b] %s" % a.medicacoes,
                                          cor=CORES["texto_suave"], tamanho="12sp",
                                          altura=dp(18)))
        return cartao


# ===========================================================================
# TELA 4 — CONFIGURAÇÕES / AJUDA
# ===========================================================================
class TelaConfig(Screen):
    def __init__(self, **kwargs):
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
        usuario = SESSAO.get("usuario") or "não conectado"
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
        # as cores já foram "desenhadas" nas telas antigas — precisa reconstruir
        # tudo para que os widgets nasçam com a paleta nova.
        App.get_running_app().reconstruir_telas(tela_atual="config")


# ===========================================================================
# APLICATIVO PRINCIPAL
# ===========================================================================
class AppVeterinaria(App):
    def build(self):
        self.title = "VacaVet — Atendimento Veterinário"
        Window.clearcolor = CORES["fundo"]
        # Em computador, simula uma tela de celular; no Android usa a tela cheia.
        if platform not in ("android", "ios"):
            Window.size = (400, 760)
            Window.minimum_width, Window.minimum_height = 360, 620

        if platform == "android":
            self._preparar_android()

        database.inicializar_banco()   # garante que o banco existe

        gerenciador = ScreenManager(transition=FadeTransition(duration=0.18))
        gerenciador.add_widget(TelaSplash(name="splash"))
        gerenciador.add_widget(TelaLogin(name="login"))
        gerenciador.add_widget(TelaInicial(name="inicial"))
        gerenciador.add_widget(TelaAtendimento(name="atendimento"))
        gerenciador.add_widget(TelaHistorico(name="historico"))
        gerenciador.add_widget(TelaConfig(name="config"))
        gerenciador.current = "splash"
        return gerenciador

    def _preparar_android(self):
        """Ajustes que só fazem sentido no celular:

        1) TECLADO: por padrão o Kivy não reposiciona a tela quando o teclado
           do Android abre, então ele cobria o campo e dava a sensação de que
           "a barra de digitação voltava atrás" (era preciso segurar o dedo).
           'below_target' faz a janela rolar para manter o campo em foco logo
           acima do teclado.

        2) PERMISSÕES: declarar RECORD_AUDIO no manifesto não basta a partir do
           Android 6; é preciso PEDIR em tempo de execução. Sem isso o app nem
           conseguia "ligar" o microfone. Pedimos ao abrir, de forma que o
           usuário veja o diálogo de permissão do sistema.
        """
        try:
            # 'pan' empurra a janela inteira para cima quando o teclado abre,
            # sem refazer o layout (o 'below_target' fazia um relayout que às
            # vezes tirava o foco do campo — sensação de "a barra volta atrás").
            Window.softinput_mode = "pan"
        except Exception:
            pass

        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.RECORD_AUDIO,
                                 Permission.INTERNET])
        except Exception:
            # Ambiente sem o módulo 'android' (ex.: rodando fora do APK): ignora.
            pass

    def reconstruir_telas(self, tela_atual="config"):
        """Recria todas as telas do zero para que peguem as cores atuais de
        CORES (as cores já foram "queimadas" nos widgets antigos ao serem
        desenhados, então trocar o tema exige reconstruir, não só repintar).
        """
        gerenciador = self.root
        gerenciador.clear_widgets()
        gerenciador.add_widget(TelaLogin(name="login"))
        gerenciador.add_widget(TelaInicial(name="inicial"))
        gerenciador.add_widget(TelaAtendimento(name="atendimento"))
        gerenciador.add_widget(TelaHistorico(name="historico"))
        gerenciador.add_widget(TelaConfig(name="config"))
        gerenciador.current = tela_atual

    # -----------------------------------------------------------------------
    # BACKUP AUTOMÁTICO AO FECHAR — os atendimentos já são salvos no SQLite
    # assim que o veterinário toca em "Salvar" (não ficam só na memória), mas
    # ao fechar o app fazemos uma CÓPIA extra do banco, com data/hora, como
    # proteção adicional. Se não houver espaço em disco, avisamos em vez de
    # tentar salvar silenciosamente e falhar sem o usuário saber.
    # -----------------------------------------------------------------------
    ESPACO_MINIMO_BYTES = 20 * 1024 * 1024   # 20 MB de folga mínima
    MAX_BACKUPS_GUARDADOS = 5

    def on_request_close(self, *args, **kwargs):
        ok, motivo = self._fazer_backup_seguro()
        if not ok:
            self._avisar_espaco_insuficiente(motivo)
            return True  # segura o fechamento até o usuário decidir
        return False  # espaço ok, backup feito: deixa fechar normalmente

    def _fazer_backup_seguro(self):
        """Tenta copiar o banco para dados/backups/. Devolve (ok, motivo)."""
        from backend.config import DATABASE_PATH, DATA_DIR

        if not os.path.isfile(DATABASE_PATH):
            return True, None  # nada pra fazer backup ainda (app nunca usado)

        try:
            espaco_livre = shutil.disk_usage(DATA_DIR).free
        except OSError:
            espaco_livre = None  # não deu pra checar — segue sem bloquear

        if espaco_livre is not None and espaco_livre < self.ESPACO_MINIMO_BYTES:
            livre_mb = espaco_livre / (1024 * 1024)
            return False, ("Restam apenas %.1f MB livres no armazenamento. "
                           "Seus atendimentos já salvos continuam no aparelho, "
                           "mas a cópia de segurança (backup) não será feita "
                           "agora." % livre_mb)

        try:
            pasta_backups = os.path.join(DATA_DIR, "backups")
            os.makedirs(pasta_backups, exist_ok=True)
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = os.path.join(pasta_backups, "atendimentos_%s.db" % carimbo)
            shutil.copy2(DATABASE_PATH, destino)
            self._limpar_backups_antigos(pasta_backups)
            return True, None
        except OSError as erro:
            return False, ("Não foi possível salvar a cópia de segurança "
                           "(%s). Seus atendimentos já salvos continuam no "
                           "aparelho normalmente." % erro)

    def _limpar_backups_antigos(self, pasta_backups):
        """Mantém só os N backups mais recentes para não lotar o disco."""
        arquivos = sorted(
            (f for f in os.listdir(pasta_backups) if f.endswith(".db")),
            reverse=True,
        )
        for antigo in arquivos[self.MAX_BACKUPS_GUARDADOS:]:
            try:
                os.remove(os.path.join(pasta_backups, antigo))
            except OSError:
                pass

    def _avisar_espaco_insuficiente(self, motivo):
        conteudo = Cartao(padding=dp(18), spacing=dp(14))
        conteudo.add_widget(texto_livre("[b]Pouco espaço de armazenamento[/b]",
                                        cor=CORES["terracota"], tamanho="16sp",
                                        altura=dp(26)))
        aviso_texto = texto_livre(motivo, cor=CORES["texto"], tamanho="13sp")
        aviso_texto.valign = "top"
        conteudo.add_widget(aviso_texto)

        linha_botoes = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        botao_cancelar = Botao(texto="Cancelar", cor=CORES["cartao"],
                               cor_texto=CORES["texto_suave"], borda=CORES["borda"])
        botao_fechar = Botao(texto="Fechar mesmo assim", cor=CORES["terracota"])
        linha_botoes.add_widget(botao_cancelar)
        linha_botoes.add_widget(botao_fechar)
        conteudo.add_widget(linha_botoes)

        popup = Popup(title="", separator_height=0, content=conteudo,
                      size_hint=(0.88, 0.42), background="",
                      background_color=(0, 0, 0, 0.55), auto_dismiss=False)
        botao_cancelar.bind(on_release=popup.dismiss)

        def fechar_mesmo_assim(*_):
            popup.dismiss()
            self.stop()

        botao_fechar.bind(on_release=fechar_mesmo_assim)
        popup.open()


if __name__ == "__main__":
    AppVeterinaria().run()
