"""
main.py (raiz do projeto)
-------------------------
Ponto de entrada do aplicativo. Tanto o PyInstaller (para gerar o .exe) quanto
o Buildozer (para gerar o APK Android) procuram um 'main.py' na raiz.

Este arquivo apenas chama o app que está em frontend/main.py.
"""

import os
import sys

# Garante que o Python encontre as pastas 'backend' e 'frontend'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Desliga a simulação de multitouch do Kivy no mouse: por padrão, botão
# direito/do meio do mouse simula um "segundo dedo" e deixa uma bolinha
# vermelha permanente na tela. Isso é só um recurso de teste para telas
# touch e não faz sentido num app de computador. Precisa ser configurado
# ANTES de importar qualquer coisa do Kivy.
from kivy.config import Config
Config.set("input", "mouse", "mouse,disable_multitouch")

from frontend.main import AppVeterinaria

if __name__ == "__main__":
    AppVeterinaria().run()
