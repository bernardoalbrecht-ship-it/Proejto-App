"""
screens/ronda.py — Nova Ronda: ao entrar, já abre o gravador GRANDE e começa a
ouvir sozinho (sem precisar tocar de novo). Ao tocar para PARAR, o app salva um
.txt com tudo o que foi dito (cópia de segurança), separa a fala por animal
("vaca N ...") criando um atendimento por animal, e tenta enviar direto à
planilha do Google — tudo automático, sem passos extras.
"""

import re
from datetime import datetime

from kivy.clock import Clock
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
from vetvoice.shared import config


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
            "%s  Já estou ouvindo. Diga o NÚMERO de cada animal antes dos "
            "dados: [b]\"vaca 12 inseminação, prenha... vaca 15 mastite, 5ml "
            "de ceftiofur\"[/b]. Não paro sozinha — toque no botão quando "
            "terminar a ronda inteira, que eu salvo e envio tudo sozinha."
            % rotulo_icone("lampada", "").rstrip(),
            cor=CORES["marrom"], tamanho="13sp", altura=dp(110)))
        corpo.add_widget(dica)

        self.lbl_prop = texto_livre("", cor=CORES["texto"], tamanho="14sp",
                                    altura=dp(24))
        corpo.add_widget(self.lbl_prop)

        # Gravador GRANDE — é a peça central da tela, não um botão a mais.
        cartao = Cartao()
        self.botao_gravar = ControleGravacao(
            ao_tocar=self.gravar, diametro=dp(140),
            rotulo=rotulo_icone("microfone", "TOQUE PARA GRAVAR A RONDA"))
        cartao.add_widget(self.botao_gravar)
        cartao.add_widget(etiqueta("Transcrição da ronda (dá para editar)"))
        self.transcricao = Campo(
            hint_text="A fala aparece aqui — ou digite/cole o texto",
            size_hint_y=None, height=dp(160))
        cartao.add_widget(self.transcricao)
        corpo.add_widget(cartao)

        botao_processar = Botao(
            texto=rotulo_icone("salvar", "Processar de novo (se editar o texto)"),
            cor=CORES["verde_claro"], size_hint_y=None, height=dp(48),
            font_size="14sp")
        botao_processar.bind(on_release=self.processar)
        corpo.add_widget(botao_processar)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def on_pre_enter(self):
        prop = self.servicos.sessao.propriedade or "—"
        self.lbl_prop.text = "Fazenda: [b]%s[/b]" % prop

    def on_enter(self):
        # A intenção de tocar em "Nova ronda" já É a intenção de gravar — não
        # faz sentido pedir um segundo toque. Começa a ouvir sozinha ao abrir
        # a tela (só se ainda não há nada gravado nem em andamento).
        if not self.transcricao.text.strip() and not getattr(
                self, "_sessao_audio", None):
            Clock.schedule_once(lambda *_: self.gravar(), 0.3)

    def gravar(self, *_):
        # Gravação contínua: não se desliga no silêncio; para no 2º toque.
        # Ao parar (ao_final), processa e envia tudo sozinha.
        alternar_gravacao(self.servicos, self, self.botao_gravar,
                          self.transcricao, ao_final=self._ao_finalizar)

    def on_leave(self):
        sessao = getattr(self, "_sessao_audio", None)
        if sessao is not None:
            try:
                sessao.cancelar()
            except Exception:
                pass
            self._sessao_audio = None

    def _ao_finalizar(self, _texto_final):
        # Chamado sozinho quando o usuário toca para PARAR a gravação —
        # é aqui que a ronda vira .txt, atendimentos e (se der) planilha.
        self.processar()

    def _salvar_txt(self, propriedade, texto):
        nome = "%s_%s.txt" % (
            datetime.now().strftime("%Y%m%d_%H%M%S"),
            re.sub(r"[^A-Za-z0-9]+", "_", propriedade).strip("_") or "fazenda")
        try:
            (config.RONDAS_DIR / nome).write_text(texto, encoding="utf-8")
            return nome
        except Exception:
            return None

    def processar(self, *_):
        texto = self.transcricao.text.strip()
        if not texto:
            aviso("Ronda vazia", "Grave ou digite a ronda antes de processar.")
            return
        propriedade = self.servicos.sessao.propriedade.strip()
        if not propriedade:
            # Voz primeiro: se a fazenda foi DITA na gravação ("estou na
            # fazenda Boa Vista, vaca 12..."), usa ela — não faz o veterinário
            # voltar de tela para digitar o que ele acabou de falar.
            propriedade = (self.servicos.analise.analisar(texto)
                           .get("propriedade") or "").strip()
            if propriedade:
                self.servicos.sessao.propriedade = propriedade
                self.servicos.propriedades.adicionar(propriedade)
        if not propriedade:
            aviso("Falta a fazenda",
                  "Diga o nome da fazenda na gravação (ex.: \"fazenda Boa "
                  "Vista, vaca 12...\") ou defina a propriedade na tela "
                  "inicial antes da ronda.")
            return
        segmentos = segmentar_por_animal(texto)
        if not segmentos:
            aviso("Nenhum animal identificado",
                  "Diga o número de cada animal (ex.: \"vaca 12 ...\") para eu "
                  "separar os atendimentos.")
            return

        arquivo_txt = self._salvar_txt(propriedade, texto)

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
        corpo = ("%d atendimento(s) criado(s) na fazenda %s.\nAnimais: %s"
                 % (len(salvos), propriedade, lista))
        if arquivo_txt:
            corpo += "\n\nCópia de segurança salva: %s" % arquivo_txt

        # Tenta enviar direto à planilha (só funciona logado no Google); se
        # não der, cai para o modo local — sem travar a ronda por causa disso.
        resultado = self.servicos.sincronizacao.executar(propriedade)
        if resultado.get("modo") == "simulado":
            corpo += ("\n\nAinda não sincronizado com o Google — entre com "
                       "sua conta na aba Ajustes e toque em Sincronizar.")
        elif resultado.get("erros"):
            corpo += ("\n\nNão consegui enviar à planilha agora (%s). Toque em "
                       "Sincronizar na tela inicial para tentar de novo."
                       % resultado.get("detalhe", "tente de novo"))
        else:
            corpo += "\n\nEnviado à planilha do Google."
            if resultado.get("link"):
                corpo += "\n%s" % resultado["link"]

        aviso("Ronda salva", corpo)
