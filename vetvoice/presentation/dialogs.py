"""
presentation/dialogs.py
-----------------------
Janelas de aviso e de confirmação, estilizadas com a paleta do app.
"""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

from vetvoice.presentation.theme import CORES, rotulo_icone
from vetvoice.presentation.widgets import Botao, Cartao, texto_livre


def aviso(titulo, mensagem):
    """Janelinha de aviso com um botão OK."""
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
    """Confirmação com Cancelar e uma ação destrutiva (vermelho). Só chama
    `ao_confirmar` se o usuário confirmar."""
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
