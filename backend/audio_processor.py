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
import time

from backend import config

_MODELO_VOSK = None  # cache: o modelo só é carregado uma vez por execução


def vosk_disponivel() -> bool:
    """Verifica (sem carregar o modelo inteiro) se dá pra usar transcrição
    ao vivo: precisa do pacote instalado E do modelo baixado."""
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
                                       silencio_para_parar: float = 2.2) -> str:
    """
    Transcreve AO VIVO usando o Vosk (offline): a cada pedacinho de áudio
    reconhecido, chama callback_parcial(texto_ate_agora) — dá pra usar isso
    pra ir mostrando a frase sendo escrita na tela, como uma legenda.

    Para sozinho quando: passa da duração máxima, OU já falou algo e ficou
    em silêncio por `silencio_para_parar` segundos (sensação mais natural do
    que esperar sempre o tempo máximo).

    Retorna o texto final reconhecido (string vazia se nada foi entendido).
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
