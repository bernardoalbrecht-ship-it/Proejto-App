"""
audio_processor.py
------------------
Responsável por transformar a FALA do veterinário em TEXTO.

Modos disponíveis, em ordem de preferência:
  1) TEMPO REAL (Vosk, offline, gratuito): vai ESCREVENDO a frase na tela
     enquanto o veterinário fala (igual legenda ao vivo), sem precisar de
     internet. Usa um modelo pequeno (~50MB) que já vem no projeto. Ativa por
     padrão (USAR_VOSK_TEMPO_REAL = True no config.py); se o modelo ou o
     pacote 'vosk' não estiverem disponíveis, cai automaticamente para o modo
     gratuito abaixo.
  2) MODO GRATUITO (reserva): usa a biblioteca 'speech_recognition' com o
     serviço gratuito do Google Web. Só transcreve DEPOIS que a pessoa para
     de falar (não é ao vivo) e precisa de internet.
  3) MODO PROFISSIONAL: usa o Google Cloud Speech-to-Text (pago, mais
     preciso). Ativa quando USAR_GOOGLE_CLOUD_SPEECH = True no config.py.
"""

import json
import os
import threading
import time

from backend import config

_MODELO_VOSK = None  # cache: o modelo só é carregado uma vez por execução


def _no_android() -> bool:
    """True quando o código está rodando dentro do APK (python-for-android
    define a variável de ambiente ANDROID_ARGUMENT). Serve para escolher o
    caminho de áudio nativo do celular em vez do pyaudio/vosk do desktop."""
    return "ANDROID_ARGUMENT" in os.environ


# ===========================================================================
# TRANSCRIÇÃO AO VIVO — API única usada pela interface
# ---------------------------------------------------------------------------
# iniciar_transcricao_ao_vivo(...) começa a ouvir e devolve uma "sessão" com
# um método .parar(). Enquanto ouve, chama callback_parcial(texto) várias
# vezes (legenda ao vivo) e, ao terminar, callback_final(texto). Se algo der
# errado, callback_erro(codigo_ou_mensagem).
#
#   • No ANDROID: usa android.speech.SpeechRecognizer (motor do sistema), com
#     resultados PARCIAIS (ao vivo) e preferência OFFLINE quando o pacote de
#     voz em português está instalado no aparelho.
#   • No DESKTOP: usa o Vosk (offline) numa thread, com um sinal de parada.
# ===========================================================================

# Mantém referências vivas dos objetos Java enquanto a gravação acontece
# (o coletor de lixo do Python não pode recolher o listener no meio do uso).
_SESSAO_ATIVA = None


def mensagem_erro_audio(codigo) -> str:
    """Traduz o código de erro do SpeechRecognizer do Android (int) numa
    explicação em português. Para o desktop, o 'codigo' já é um texto."""
    mapa = {
        1: "O reconhecimento demorou demais (rede lenta). Tente de novo.",
        2: "Sem conexão com a internet. Conecte-se ou instale o pacote de "
           "voz offline em português (Config. do Android > Idiomas/Voz).",
        3: "Não consegui acessar o microfone. Verifique a permissão do app.",
        4: "O servidor de reconhecimento falhou. Tente novamente.",
        5: "Erro interno do reconhecimento. Tente novamente.",
        6: "Não ouvi nenhuma fala. Toque em gravar e fale mais perto.",
        7: "Não entendi o que foi dito. Pode repetir?",
        8: "O reconhecimento está ocupado. Aguarde um instante e tente de novo.",
        9: "Faltou a permissão de microfone. Autorize o app nas configurações.",
        11: "O serviço de voz desconectou. Tente novamente.",
        12: "Idioma não suportado neste aparelho.",
        13: "O pacote de voz em português não está instalado para uso "
            "offline. Instale-o em Config. do Android (Voz/Assistente) ou "
            "conecte-se à internet.",
    }
    if isinstance(codigo, int):
        return mapa.get(codigo, "Não consegui captar o áudio (erro %d)." % codigo)
    return str(codigo) or "Não consegui captar o áudio."


def iniciar_transcricao_ao_vivo(callback_parcial=None, callback_final=None,
                                callback_erro=None, preferir_offline=True):
    """Começa a ouvir o microfone e transcrever AO VIVO. Devolve uma sessão
    com .parar() para encerrar a captação (botão 'Parar')."""
    global _SESSAO_ATIVA
    # ATENÇÃO: _no_android() é True quando o app está RODANDO NO Android
    # (dentro do APK). A versão anterior estava com os ramos TROCADOS: no
    # celular caía no caminho do desktop (Vosk/speech_recognition, que não
    # existem no APK) e a "gravação" terminava na hora com texto vazio — o
    # botão parecia não fazer nada. Agora cada plataforma usa o seu motor.
    if _no_android():
        _SESSAO_ATIVA = _iniciar_android(callback_parcial, callback_final,
                                         callback_erro, preferir_offline)
    else:
        _SESSAO_ATIVA = _iniciar_desktop(callback_parcial, callback_final,
                                         callback_erro)
    return _SESSAO_ATIVA


# ---------------------------------------------------------------------------
# ANDROID — SpeechRecognizer (ao vivo, com preferência offline)
# ---------------------------------------------------------------------------
def _iniciar_android(callback_parcial, callback_final, callback_erro,
                     preferir_offline):
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread

    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    Intent = autoclass("android.content.Intent")
    PythonActivity = autoclass("org.kivy.android.PythonActivity")

    RESULTS = SpeechRecognizer.RESULTS_RECOGNITION

    def _texto_do_bundle(bundle):
        try:
            lista = bundle.getStringArrayList(RESULTS)
            if lista is not None and lista.size() > 0:
                return lista.get(0)
        except Exception:
            pass
        return ""

    class _Listener(PythonJavaClass):
        __javainterfaces__ = ["android/speech/RecognitionListener"]
        __javacontext__ = "app"

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, results):
            if callback_parcial:
                texto = _texto_do_bundle(results)
                if texto:
                    callback_parcial(texto)

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):
            if callback_final:
                callback_final(_texto_do_bundle(results))

        @java_method("(I)V")
        def onError(self, erro):
            if callback_erro:
                callback_erro(int(erro))

        # métodos obrigatórios da interface (não precisamos deles) --------
        @java_method("(Landroid/os/Bundle;)V")
        def onReadyForSpeech(self, params):
            pass

        @java_method("()V")
        def onBeginningOfSpeech(self):
            pass

        @java_method("(F)V")
        def onRmsChanged(self, rmsdB):
            pass

        @java_method("([B)V")
        def onBufferReceived(self, buffer):
            pass

        @java_method("()V")
        def onEndOfSpeech(self):
            pass

        @java_method("(ILandroid/os/Bundle;)V")
        def onEvent(self, eventType, params):
            pass

    class _SessaoAndroid:
        def __init__(self):
            self._recognizer = None
            self._listener = _Listener()

        def _criar_intent(self):
            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, config.IDIOMA)
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
            # Modo ditado: não corta no primeiro silêncio curto.
            intent.putExtra("android.speech.extra.DICTATION_MODE", True)
            # Tolera PAUSAS mais longas antes de encerrar (o veterinário fala
            # em blocos: "vaca 324..." <pausa> "...inseminação"). Sem isto o
            # motor encerrava no primeiro silêncio. São dicas — nem todo motor
            # respeita, mas não atrapalham.
            intent.putExtra(
                "android.speech.extra.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS",
                4000)
            intent.putExtra(
                "android.speech.extra."
                "SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS", 4000)
            intent.putExtra(
                "android.speech.extra.SPEECH_INPUT_MINIMUM_LENGTH_MILLIS",
                12000)
            if preferir_offline:
                try:
                    intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, True)
                except Exception:
                    pass
            return intent

        @run_on_ui_thread
        def iniciar(self):
            if not SpeechRecognizer.isRecognitionAvailable(
                    PythonActivity.mActivity):
                if callback_erro:
                    callback_erro("Este aparelho não tem reconhecimento de "
                                  "voz do Google. Digite o texto à mão.")
                return
            self._recognizer = SpeechRecognizer.createSpeechRecognizer(
                PythonActivity.mActivity)
            self._recognizer.setRecognitionListener(self._listener)
            self._recognizer.startListening(self._criar_intent())

        @run_on_ui_thread
        def parar(self):
            if self._recognizer is not None:
                try:
                    self._recognizer.stopListening()
                except Exception:
                    pass

        @run_on_ui_thread
        def cancelar(self):
            if self._recognizer is not None:
                try:
                    self._recognizer.cancel()
                    self._recognizer.destroy()
                except Exception:
                    pass
                self._recognizer = None

    sessao = _SessaoAndroid()
    sessao.iniciar()
    return sessao


# ---------------------------------------------------------------------------
# DESKTOP — Vosk offline numa thread, com sinal de parada
# ---------------------------------------------------------------------------
class _SessaoDesktop:
    def __init__(self, parar_flag):
        self._parar = parar_flag

    def parar(self):
        self._parar.set()

    def cancelar(self):
        self._parar.set()


def _iniciar_desktop(callback_parcial, callback_final, callback_erro):
    parar_flag = threading.Event()

    def tarefa():
        try:
            if _vosk_desktop_disponivel():
                texto = transcrever_streaming_do_microfone(
                    callback_parcial=callback_parcial, parar_flag=parar_flag)
            else:
                texto = _transcrever_gratuito(15)
                if texto and callback_parcial:
                    callback_parcial(texto)
        except Exception as erro:
            if callback_erro:
                callback_erro(str(erro))
            texto = ""
        if callback_final:
            callback_final(texto or "")

    threading.Thread(target=tarefa, daemon=True).start()
    return _SessaoDesktop(parar_flag)


def _vosk_desktop_disponivel() -> bool:
    if not config.USAR_VOSK_TEMPO_REAL:
        return False
    try:
        import vosk  # noqa: F401
    except ImportError:
        return False
    return config.VOSK_MODEL_PATH.is_dir()


def vosk_disponivel() -> bool:
    """Verifica (sem carregar o modelo inteiro) se dá pra usar transcrição
    ao vivo: precisa do pacote instalado E do modelo baixado."""
    if _no_android():
        # No celular usamos o reconhecimento nativo do Android (diálogo do
        # sistema), que não é "ao vivo" — então o app usa o caminho comum.
        return False
    if not config.USAR_VOSK_TEMPO_REAL:
        return False
    try:
        import vosk  # noqa: F401
    except ImportError:
        return False
    return config.VOSK_MODEL_PATH.is_dir()


def _carregar_modelo_vosk():
    global _MODELO_VOSK
    if _MODELO_VOSK is not None:
        return _MODELO_VOSK
    from vosk import Model
    _MODELO_VOSK = Model(str(config.VOSK_MODEL_PATH))
    return _MODELO_VOSK


def transcrever_do_microfone(duracao_maxima: int = 15) -> str:
    """
    Grava do microfone e devolve o texto reconhecido (sem atualização ao
    vivo). Mantido para compatibilidade e como reserva de última instância.
    Retorna string vazia se não conseguir (sem microfone, sem internet, etc.).
    """
    if config.USAR_GOOGLE_CLOUD_SPEECH:
        return _transcrever_google_cloud()
    return _transcrever_gratuito(duracao_maxima)


def transcrever_streaming_do_microfone(callback_parcial=None,
                                       duracao_maxima: int = 20,
                                       silencio_para_parar: float = 2.2,
                                       parar_flag=None) -> str:
    """
    Transcreve AO VIVO usando o Vosk (offline): a cada pedacinho de áudio
    reconhecido, chama callback_parcial(texto_ate_agora) — dá pra usar isso
    pra ir mostrando a frase sendo escrita na tela, como uma legenda.

    Para sozinho quando: passa da duração máxima, OU já falou algo e ficou
    em silêncio por `silencio_para_parar` segundos (sensação mais natural do
    que esperar sempre o tempo máximo).

    Retorna o texto final reconhecido (string vazia se nada foi entendido).
    Se `parar_flag` (threading.Event) for passado, encerra assim que ele for
    setado — é assim que o botão "Parar" interrompe a captação no desktop.
    """
    import pyaudio

    modelo = _carregar_modelo_vosk()
    from vosk import KaldiRecognizer

    reconhecedor = KaldiRecognizer(modelo, config.TAXA_AMOSTRAGEM)

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1,
                     rate=config.TAXA_AMOSTRAGEM, input=True,
                     frames_per_buffer=4000)
    stream.start_stream()

    partes_confirmadas = []
    inicio = time.time()
    ultima_vez_com_fala = None

    try:
        while True:
            if parar_flag is not None and parar_flag.is_set():
                break
            agora = time.time()
            if agora - inicio > duracao_maxima:
                break
            if (ultima_vez_com_fala is not None
                    and agora - ultima_vez_com_fala > silencio_para_parar):
                break

            dados = stream.read(4000, exception_on_overflow=False)

            if reconhecedor.AcceptWaveform(dados):
                texto = json.loads(reconhecedor.Result()).get("text", "").strip()
                if texto:
                    partes_confirmadas.append(texto)
                    ultima_vez_com_fala = agora
                    if callback_parcial:
                        callback_parcial(" ".join(partes_confirmadas))
            else:
                parcial = json.loads(reconhecedor.PartialResult()).get(
                    "partial", "").strip()
                if parcial:
                    ultima_vez_com_fala = agora
                    if callback_parcial:
                        callback_parcial(
                            " ".join(partes_confirmadas + [parcial]))
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    texto_restante = json.loads(reconhecedor.FinalResult()).get(
        "text", "").strip()
    if texto_restante:
        partes_confirmadas.append(texto_restante)

    return " ".join(partes_confirmadas).strip()


# ---------------------------------------------------------------------------
# MODO GRATUITO — speech_recognition + Google Web (sem custo)
# ---------------------------------------------------------------------------
def _transcrever_gratuito(duracao_maxima: int) -> str:
    try:
        import speech_recognition as sr
    except ImportError:
        print("[AVISO] Biblioteca 'speech_recognition' não instalada. "
              "Rode: pip install SpeechRecognition pyaudio")
        return ""

    reconhecedor = sr.Recognizer()
    try:
        with sr.Microphone(sample_rate=config.TAXA_AMOSTRAGEM) as fonte:
            print("[ÁUDIO] Ajustando ao ruído ambiente...")
            reconhecedor.adjust_for_ambient_noise(fonte, duration=0.5)
            print("[ÁUDIO] Pode falar!")
            audio = reconhecedor.listen(fonte, timeout=5,
                                        phrase_time_limit=duracao_maxima)
    except Exception as erro:
        print(f"[ERRO] Não foi possível acessar o microfone: {erro}")
        return ""

    try:
        texto = reconhecedor.recognize_google(audio, language=config.IDIOMA)
        print(f"[ÁUDIO] Transcrito: {texto}")
        return texto
    except sr.UnknownValueError:
        print("[ÁUDIO] Não entendi o que foi dito.")
        return ""
    except sr.RequestError as erro:
        print(f"[ERRO] Serviço de reconhecimento indisponível: {erro}")
        return ""


# ---------------------------------------------------------------------------
# MODO PROFISSIONAL — Google Cloud Speech-to-Text (pago)
# ---------------------------------------------------------------------------
def _transcrever_google_cloud() -> str:
    try:
        import pyaudio
        from google.cloud import speech
    except ImportError:
        print("[AVISO] Instale: pip install google-cloud-speech pyaudio")
        return ""

    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
        config.GOOGLE_CLOUD_CREDENTIALS
    )

    cliente = speech.SpeechClient()
    configuracao = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=config.TAXA_AMOSTRAGEM,
        language_code=config.IDIOMA,
        enable_automatic_punctuation=True,
    )

    # Grava ~7 segundos de áudio do microfone
    formato, canais, quadros = pyaudio.paInt16, 1, []
    pa = pyaudio.PyAudio()
    stream = pa.open(format=formato, channels=canais,
                     rate=config.TAXA_AMOSTRAGEM, input=True,
                     frames_per_buffer=1024)
    print("[ÁUDIO] Gravando (Google Cloud)... fale agora.")
    for _ in range(0, int(config.TAXA_AMOSTRAGEM / 1024 * 7)):
        quadros.append(stream.read(1024))
    stream.stop_stream()
    stream.close()
    pa.terminate()

    audio = speech.RecognitionAudio(content=b"".join(quadros))
    resposta = cliente.recognize(config=configuracao, audio=audio)
    if resposta.results:
        return resposta.results[0].alternatives[0].transcript
    return ""
