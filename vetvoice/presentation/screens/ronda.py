"""
screens/ronda.py — Nova Ronda: grava a propriedade inteira numa gravação só e,
ao processar, separa a fala por animal ("vaca N ...") criando um atendimento
por animal. Depois é só sincronizar para enviar tudo à planilha.
"""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from vetvoice.application.atendimentos import CAMPOS_FICHA
from vetvoice.domain.parsing.segmentacao import segmentar_por_animal
from vetvoice.presentation.dialogs import aviso
from vetvoice.presentation.gravacao import alternar_gravacao
from vetvoice.presentation.theme import CORES, rotulo_icone
from vetvoice.presentation.widgets import (
    Botao, Campo, Cartao, ControleGravacao, RolagemComCampos, cabecalho,
    etiqueta, pagina, texto_livre,
)


class TelaRonda(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(cabecalho("Nova Ronda", "Grave a fazenda inteira",
                                  icone_nome="prancheta", com_voltar=True))

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(14),
                          size_hint_y=None)
        corpo.bind(minimum_height=corpo.setter("height"))

        dica = Cartao(cor=CORES["chip_pend"], borda=False)
        dica.add_widget(texto_livre(
            "%s  Fale os animais em sequência, dizendo o NÚMERO de cada um "
            "antes dos dados. Ex.: [b]\"vaca 12 inseminação, prenha... vaca 15 "
            "mastite, 5ml de ceftiofur\"[/b]. A gravação não se desliga sozinha "
            "— toque para parar. Ao processar, cada animal vira um atendimento."
            % rotulo_icone("lampada", "").rstrip(),
            cor=CORES["marrom"], tamanho="13sp", altura=dp(120)))
        corpo.add_widget(dica)

        self.lbl_prop = texto_livre("", cor=CORES["texto"], tamanho="14sp",
                                    altura=dp(24))
        corpo.add_widget(self.lbl_prop)

        cartao = Cartao()
        self.botao_gravar = ControleGravacao(
            ao_tocar=self.gravar,
            rotulo=rotulo_icone("microfone", "GRAVAR A RONDA"))
        cartao.add_widget(self.botao_gravar)
        cartao.add_widget(etiqueta("Transcrição da ronda"))
        self.transcricao = Campo(
            hint_text="A fala aparece aqui — ou digite/cole o texto",
            size_hint_y=None, height=dp(180))
        cartao.add_widget(self.transcricao)
        corpo.add_widget(cartao)

        botao_processar = Botao(
            texto=rotulo_icone("salvar", "Processar e salvar ronda"),
            cor=CORES["verde"], size_hint_y=None, height=dp(56),
            font_size="16sp")
        botao_processar.bind(on_release=self.processar)
        corpo.add_widget(botao_processar)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def on_pre_enter(self):
        prop = self.servicos.sessao.propriedade or "—"
        self.lbl_prop.text = "Fazenda: [b]%s[/b]" % prop

    def gravar(self, *_):
        # Gravação contínua: não se desliga no silêncio; para no 2º toque.
        alternar_gravacao(self.servicos, self, self.botao_gravar,
                          self.transcricao)

    def on_leave(self):
        sessao = getattr(self, "_sessao_audio", None)
        if sessao is not None:
            try:
                sessao.cancelar()
            except Exception:
                pass
            self._sessao_audio = None

    def processar(self, *_):
        texto = self.transcricao.text.strip()
        if not texto:
            aviso("Ronda vazia", "Grave ou digite a ronda antes de processar.")
            return
        propriedade = self.servicos.sessao.propriedade.strip()
        if not propriedade:
            aviso("Falta a fazenda",
                  "Defina a propriedade na tela inicial antes da ronda.")
            return
        segmentos = segmentar_por_animal(texto)
        if not segmentos:
            aviso("Nenhum animal identificado",
                  "Diga o número de cada animal (ex.: \"vaca 12 ...\") para eu "
                  "separar os atendimentos.")
            return

        sessao = self.servicos.sessao
        salvos = []
        for id_vaca, trecho in segmentos:
            dados = self.servicos.analise.analisar(trecho)
            campos = {chave: dados.get(chave, "") for chave in CAMPOS_FICHA}
            self.servicos.atendimentos.registrar(
                id_vaca=id_vaca, propriedade=propriedade,
                tipo_producao=sessao.tipo_producao,
                transcricao_original=trecho, campos=campos)
            salvos.append(id_vaca)

        self.transcricao.text = ""
        lista = ", ".join(salvos)
        aviso("Ronda salva",
              "%d atendimento(s) criado(s) na fazenda %s.\nAnimais: %s\n\n"
              "Abra o Histórico para revisar e toque em Sincronizar para "
              "enviar à planilha." % (len(salvos), propriedade, lista))
