"""
presentation/theme.py
---------------------
Identidade visual: fonte de ícones, paletas (clara/escura), a paleta ativa
(CORES) e os utilitários de desenho de fundo arredondado. Concentra tudo que é
"aparência" para que os widgets e telas só consumam CORES/ICONES.
"""

import json
import os

from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.label import Label

from vetvoice.shared import config

# ===========================================================================
# FONTE DE ÍCONES — Material Design Icons (evita "tofu" dos emojis)
# ===========================================================================
_ARQUIVO_MDI = os.path.join(config.BASE_DIR, "assets", "fonts",
                            "materialdesignicons-webfont.ttf")

FONTE_ICONES = "Icones"
if os.path.isfile(_ARQUIVO_MDI):
    LabelBase.register(name=FONTE_ICONES, fn_regular=_ARQUIVO_MDI)
else:
    FONTE_ICONES = None  # sem o .ttf, cai no texto normal sem quebrar

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
    "casa": "\U000F02DC",
}


def icone(nome, tamanho="20sp", cor=(1, 1, 1, 1)):
    """Label com um glifo da fonte de ícones (ou '?' de reserva)."""
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
    """'Markup' combinando um glifo da fonte de ícones com texto normal."""
    glifo = ICONES.get(nome, "?")
    if FONTE_ICONES:
        return "[font=%s]%s[/font]  %s" % (FONTE_ICONES, glifo, texto)
    return texto


# ===========================================================================
# PALETAS — pasto (verde), leite (creme), curral (marrom), terracota (gravar)
# ===========================================================================
# Paleta "verde natural moderno": superfícies claras e quentes, verde de pasto
# mais vivo, bordas quase imperceptíveis e bastante respiro.
PALETA_CLARA = {
    "fundo":        (0.965, 0.973, 0.961, 1),  # F6F8F5  branco-verde suave
    "verde":        (0.106, 0.545, 0.361, 1),  # 1B8B5C  pasto vivo (primária)
    "verde_claro":  (0.271, 0.706, 0.494, 1),  # 45B47E  broto
    "verde_escuro": (0.063, 0.353, 0.243, 1),  # 10593E  mata fechada
    "terracota":    (0.902, 0.380, 0.220, 1),  # E66138  gravando (parar)
    "azul":         (0.157, 0.451, 0.596, 1),  # 287398  nuvem/sincronizar
    "marrom":       (0.451, 0.404, 0.337, 1),  # 736756  couro (neutro quente)
    "cartao":       (1, 1, 1, 1),              # branco  leite
    "texto":        (0.102, 0.141, 0.122, 1),  # 1A241F  quase preto esverdeado
    "texto_suave":  (0.416, 0.451, 0.435, 1),  # 6A736F  cinza
    "texto_campo":  (0.063, 0.353, 0.243, 1),  # verde escuro ao digitar
    "borda":        (0.918, 0.933, 0.914, 1),  # EAEEEA  contorno bem suave
    "chip_ok":      (0.851, 0.937, 0.886, 1),  # verde bem claro (sincronizado)
    "chip_pend":    (0.996, 0.929, 0.812, 1),  # âmbar claro (pendente)
    "amarelo":      (0.945, 0.749, 0.259, 1),
    "gravar":       (0.106, 0.545, 0.361, 1),  # microfone em repouso = verde
}

PALETA_ESCURA = {
    "fundo":        (0.063, 0.078, 0.071, 1),  # quase preto esverdeado
    "verde":        (0.243, 0.647, 0.463, 1),  # 3EA576  mais vibrante no escuro
    "verde_claro":  (0.353, 0.749, 0.541, 1),
    "verde_escuro": (0.180, 0.463, 0.337, 1),
    "terracota":    (0.937, 0.451, 0.294, 1),
    "azul":         (0.361, 0.627, 0.788, 1),
    "marrom":       (0.612, 0.541, 0.451, 1),
    "cartao":       (0.118, 0.137, 0.129, 1),  # card escuro
    "texto":        (0.910, 0.925, 0.918, 1),  # quase branco
    "texto_suave":  (0.612, 0.647, 0.631, 1),
    "texto_campo":  (0.910, 0.925, 0.918, 1),
    "borda":        (0.216, 0.243, 0.231, 1),
    "chip_ok":      (0.851, 0.937, 0.886, 1),
    "chip_pend":    (0.996, 0.929, 0.812, 1),
    "amarelo":      (0.976, 0.804, 0.333, 1),
    "gravar":       (0.243, 0.647, 0.463, 1),
}

CORES = dict(PALETA_CLARA)  # dict MUTÁVEL — trocamos os valores ao mudar de tema
TEMA = {"escuro": False}


def _arquivo_preferencias():
    return os.path.join(config.DATA_DIR, "preferencias.json")


def _carregar_tema_salvo():
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
        try:
            with open(_arquivo_preferencias(), "w", encoding="utf-8") as f:
                json.dump({"tema_escuro": escuro}, f)
        except OSError:
            pass


# Carrega o tema salvo ao importar (antes de qualquer widget ser criado).
TEMA["escuro"] = _carregar_tema_salvo()
if TEMA["escuro"]:
    CORES.clear()
    CORES.update(PALETA_ESCURA)


def escurecer(cor, f=0.82):
    r, g, b, a = cor
    return (r * f, g * f, b * f, a)


def pintar_fundo(widget, cor, raio=14, borda=None, largura=1.2):
    """Desenha um retângulo arredondado atrás de qualquer widget.

    IMPORTANTE: as instruções de Color ficam "ativas" até a PRÓXIMA Color,
    mesmo atravessando canvas.before -> canvas do widget. Sem resetar para
    branco no final, a última cor (ex.: da borda) "vazava" e tingia o TEXTO
    desenhado depois pelo próprio widget.
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
