"""
screens/atendimento.py — Ficha do atendimento: identificação da vaca, gravação
por voz, campos preenchidos pelo parser e salvar.
"""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from vetvoice.presentation.dialogs import aviso
from vetvoice.presentation.gravacao import alternar_gravacao
from vetvoice.presentation.theme import CORES, rotulo_icone
from vetvoice.presentation.widgets import (
    Botao, Campo, Cartao, ControleGravacao, RolagemComCampos, SeletorComOutro,
    SeletorOpcoes, cabecalho, etiqueta, pagina, texto_livre,
)
from vetvoice.shared import config
from vetvoice.shared.config import COLUNAS_EXIBICAO


class TelaAtendimento(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(cabecalho("Novo Atendimento", "Fale ou digite os dados",
                                  icone_nome="estetoscopio", com_voltar=True))

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(14),
                          size_hint_y=None)
        corpo.bind(minimum_height=corpo.setter("height"))

        # --- Cartão: identificação da vaca + gravação ---
        topo = Cartao()
        topo.add_widget(etiqueta("Vaca (brinco)"))
        self.campo_id = Campo(multiline=False, hint_text="Ex: 123",
                              size_hint_y=None, height=dp(48), font_size="17sp")
        topo.add_widget(self.campo_id)

        self.botao_gravar = ControleGravacao(
            ao_tocar=self.gravar,
            rotulo=rotulo_icone("estrelas", "FALAR E PREENCHER A FICHA"))
        topo.add_widget(self.botao_gravar)

        topo.add_widget(etiqueta("Transcrição (fala ou digitação)"))
        self.transcricao = Campo(
            hint_text="A fala aparece aqui — ou digite para testar",
            size_hint_y=None, height=dp(74))
        topo.add_widget(self.transcricao)

        botao_analisar = Botao(
            texto=rotulo_icone("estrelas", "Preencher campos a partir da fala"),
            cor=CORES["verde_claro"], size_hint_y=None, height=dp(48),
            font_size="15sp")
        botao_analisar.bind(on_release=self.analisar_texto)
        topo.add_widget(botao_analisar)
        corpo.add_widget(topo)

        # --- Cartão: campos do atendimento ---
        ficha = Cartao()
        ficha.add_widget(texto_livre("[b]Ficha do atendimento[/b]",
                                     cor=CORES["verde"], tamanho="15sp",
                                     altura=dp(24)))
        self.campos = {}
        multilinha = ("observacoes",)
        dic = self.servicos.dicionarios
        for chave in ["procedimento", "raca", "peso_kg", "idade_anos",
                      "status_reprodutivo", "diagnostico", "medicacoes",
                      "proxima_acao", "observacoes"]:
            ficha.add_widget(etiqueta(COLUNAS_EXIBICAO[chave]))

            if chave == "procedimento":
                entrada = SeletorComOutro(
                    dic.opcoes("procedimento", config.PROCEDIMENTO_OPCOES),
                    ao_adicionar=lambda t: dic.adicionar("procedimento", t),
                    cols=2)
                ficha.add_widget(entrada)

            elif chave == "raca":
                entrada = SeletorComOutro(
                    dic.opcoes("raca", config.RACA_OPCOES),
                    ao_adicionar=lambda t: dic.adicionar("raca", t), cols=3)
                ficha.add_widget(entrada)

            elif chave == "status_reprodutivo":
                # Escolha entre Prenha/Vazia; o valor fica num Campo "oculto".
                entrada = Campo()
                self.seletor_status = SeletorOpcoes(
                    config.STATUS_REPRODUTIVO_OPCOES,
                    ao_selecionar=lambda v, e=entrada: setattr(e, "text", v))
                ficha.add_widget(self.seletor_status)

            elif chave == "diagnostico":
                base_diag = [d for d in config.DIAGNOSTICO_OPCOES if d != "Outro"]
                entrada = SeletorComOutro(
                    dic.opcoes("diagnostico", base_diag),
                    ao_adicionar=lambda t: dic.adicionar("diagnostico", t),
                    cols=2)
                ficha.add_widget(entrada)

            else:
                entrada = Campo(multiline=(chave in multilinha), size_hint_y=None,
                                height=dp(64) if chave in multilinha else dp(44))
                ficha.add_widget(entrada)

            self.campos[chave] = entrada
        corpo.add_widget(ficha)

        # --- Ações inferiores ---
        rodape = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(12))
        botao_voltar = Botao(texto="Voltar", cor=CORES["marrom"])
        botao_voltar.bind(on_release=lambda *_: setattr(self.manager,
                                                        "current", "inicial"))
        botao_salvar = Botao(texto=rotulo_icone("salvar", "Salvar"),
                             cor=CORES["verde"])
        botao_salvar.bind(on_release=self.salvar)
        rodape.add_widget(botao_voltar)
        rodape.add_widget(botao_salvar)
        corpo.add_widget(rodape)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def on_pre_enter(self):
        # limpa a tela para um novo atendimento
        self.campo_id.text = ""
        self.transcricao.text = ""
        for entrada in self.campos.values():
            entrada.text = ""
        self.seletor_status.selecionar("", disparar_callback=False)

        # Veio um comando falado da tela inicial? Preenche a ficha a partir dele.
        comando = self.servicos.sessao.consumir_prefill()
        if comando:
            self.transcricao.text = comando
            self.analisar_texto()

    def gravar(self, *_):
        alternar_gravacao(self.servicos, self, self.botao_gravar,
                          self.transcricao,
                          ao_final=lambda _t: self.analisar_texto())

    def on_leave(self):
        sessao = getattr(self, "_sessao_audio", None)
        if sessao is not None:
            try:
                sessao.cancelar()
            except Exception:
                pass
            self._sessao_audio = None

    def analisar_texto(self, *_):
        texto = self.transcricao.text.strip()
        if not texto:
            aviso("Atenção", "Não há texto para analisar.")
            return
        campos = self.servicos.analise.analisar(texto)
        if campos.get("id_vaca") and not self.campo_id.text.strip():
            self.campo_id.text = campos["id_vaca"]
        # procedimento, raça e diagnóstico são SeletorComOutro: o próprio widget
        # destaca o chip certo ou, se o valor não existir, abre o campo "Outro".
        for chave, entrada in self.campos.items():
            if campos.get(chave):
                entrada.text = campos[chave]
        if campos.get("status_reprodutivo"):
            self.seletor_status.selecionar(campos["status_reprodutivo"],
                                           disparar_callback=False)

    def salvar(self, *_):
        if not self.campo_id.text.strip():
            aviso("Atenção", "Informe o número do brinco da vaca.")
            return
        sessao = self.servicos.sessao
        campos = {chave: entrada.text for chave, entrada in self.campos.items()}
        atendimento = self.servicos.atendimentos.registrar(
            id_vaca=self.campo_id.text,
            propriedade=sessao.propriedade,
            tipo_producao=sessao.tipo_producao,
            transcricao_original=self.transcricao.text,
            campos=campos)
        aviso("Salvo", "Atendimento da vaca %s salvo!\nSerá enviado à nuvem na "
              "próxima sincronização." % atendimento.id_vaca)
        self.on_pre_enter()
