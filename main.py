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

from vetvoice.presentation.app import AppVeterinaria

if __name__ == "__main__":
    AppVeterinaria().run()
