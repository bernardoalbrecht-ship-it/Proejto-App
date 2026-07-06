"""
presentation/gravacao.py
------------------------
Liga/desliga a captação de voz AO VIVO (toggle), compartilhada pela nota rápida
(tela inicial) e pelo atendimento. Depende só dos casos de uso (`servicos`):
transcrição e correção do texto — nenhuma regra de negócio aqui.
"""

from kivy.clock import Clock

from vetvoice.presentation.dialogs import aviso


def alternar_gravacao(servicos, host, botao, campo, ao_final=None):
    """- 1º toque: começa a ouvir; o botão fica FIXO em 'gravando' e a
      transcrição vai aparecendo no `campo` (resultados parciais).
    - 2º toque (ou fim automático): para a captação.

    Guarda a sessão de áudio em host._sessao_audio."""
    sessao = getattr(host, "_sessao_audio", None)
    if sessao is not None:
        try:
            sessao.parar()
        except Exception:
            pass
        return

    # Texto que JÁ estava no campo: vamos ACRESCENTAR a fala, não apagar.
    # Assim gravar de novo continua de onde parou (ditar em blocos:
    # "vaca 324" + "inseminação" = "vaca 324 inseminação").
    base = campo.text.strip()

    def _juntar(novo):
        novo = (novo or "").strip()
        if base and novo:
            return base + " " + novo
        return base or novo

    def _repor_botao(*_):
        botao.set_estado(False)

    def on_parcial(texto):
        Clock.schedule_once(lambda *_: setattr(campo, "text", _juntar(texto)))

    def on_final(texto):
        texto = (texto or "").strip()
        if texto:
            texto = servicos.analise.corrigir(texto)
        final = _juntar(texto)

        def _ui(*_):
            host._sessao_audio = None
            _repor_botao()
            if final:
                campo.text = final
                if ao_final and texto:
                    ao_final(final)
        Clock.schedule_once(_ui)

    def on_erro(codigo):
        def _ui(*_):
            host._sessao_audio = None
            _repor_botao()
            aviso("Áudio", servicos.transcritor.mensagem_erro(codigo))
        Clock.schedule_once(_ui)

    try:
        host._sessao_audio = servicos.transcritor.iniciar_ao_vivo(
            callback_parcial=on_parcial, callback_final=on_final,
            callback_erro=on_erro)
    except Exception as erro:
        host._sessao_audio = None
        aviso("Áudio", "Não foi possível iniciar a captação de voz. Você "
              "pode digitar o texto manualmente.\n\n(%s)" % erro)
        return

    botao.set_estado(True)
