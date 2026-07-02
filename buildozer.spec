[app]

# Nome que aparece no celular
title = Atendimento Veterinario

# Nome do pacote (sem espaços, sem acentos)
package.name = atendimentovet
package.domain = br.com.veterinaria

# Onde está o código-fonte
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,db,ttf

# Versão do app
version = 1.0

# Bibliotecas que o app precisa (Kivy + transcrição + áudio)
# OBS: vosk e audiostream têm compilação nativa e são os pontos que mais
# quebram o primeiro build. Se falhar, use a "build mínima" do notebook
# (comenta vosk/audiostream) só para ter um APK que abre e roda a interface.
requirements = python3,kivy,speechrecognition,openpyxl,audiostream,plyer,vosk

# Aceita automaticamente as licenças do Android SDK (evita travar o build)
android.accept_sdk_license = True

# Arquivo principal a ser executado
# (aponta para frontend/main.py)
# O Buildozer procura main.py na raiz; veja a nota no README sobre isso.

# Orientação da tela
orientation = portrait

# PERMISSÕES DO ANDROID (essenciais!)
# RECORD_AUDIO   -> usar o microfone
# INTERNET       -> transcrição e sincronização
android.permissions = INTERNET, RECORD_AUDIO, ACCESS_NETWORK_STATE

# Versões do Android
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a

# Ícone (coloque um arquivo icon.png na raiz se quiser personalizar)
# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
