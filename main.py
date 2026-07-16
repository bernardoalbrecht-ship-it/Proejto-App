"""
main.py (raiz do projeto)
-------------------------
Ponto de entrada do aplicativo. Tanto o PyInstaller (para gerar o .exe) quanto
o Buildozer (para gerar o APK Android) procuram um 'main.py' na raiz.

Este arquivo apenas inicia o app da camada de apresentação (vetvoice.presentation).
"""

import os
import sys

# Garante que o Python encontre o pacote 'vetvoice'.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Desliga a simulação de multitouch do mouse (o botão direito deixava uma
# bolinha vermelha permanente na tela). Precisa vir ANTES de importar o Kivy.
from kivy.config import Config
Config.set("input", "mouse", "mouse,disable_multitouch")

def _tela_de_erro(texto):
    """Último recurso: se o app quebrar na inicialização, mostra o erro NA TELA
    em vez de fechar em silêncio — sem isso, um crash no Android vira só
    "o app não abre" e ninguém descobre a causa sem logcat."""
    from kivy.app import App
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.label import Label

    class AppErro(App):
        def build(self):
            raiz = ScrollView()
            lbl = Label(text=texto, size_hint_y=None, padding=(24, 24),
                        font_size="13sp", halign="left", valign="top")
            lbl.bind(width=lambda l, w: setattr(l, "text_size", (w - 48, None)))
            lbl.bind(texture_size=lambda l, t: setattr(l, "height", t[1] + 48))
            raiz.add_widget(lbl)
            return raiz

    AppErro().run()


if __name__ == "__main__":
    try:
        from vetvoice.presentation.app import AppVeterinaria
        AppVeterinaria().run()
    except Exception:
        import traceback
        erro = traceback.format_exc()
        try:  # também grava em arquivo, para consulta posterior
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "crash.log"), "w", encoding="utf-8") as f:
                f.write(erro)
        except OSError:
            pass
        _tela_de_erro("O VetVoice encontrou um erro ao abrir.\n\n"
                      "Tire um print desta tela e envie ao suporte:\n\n" + erro)
