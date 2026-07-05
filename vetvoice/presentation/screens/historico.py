"""
screens/historico.py — Histórico agrupado por vaca (por fazenda), com filtro por
número da vaca, detalhe completo em popup e exclusão de atendimentos/vacas.
"""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from vetvoice.presentation.dialogs import confirmar
from vetvoice.presentation.theme import CORES, pintar_fundo, rotulo_icone
from vetvoice.presentation.widgets import (
    Botao, Campo, Cartao, CartaoClicavel, RolagemComCampos, SeletorOpcoes,
    chip, etiqueta, pagina, texto_livre, titulo_tela,
)


class TelaHistorico(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = pagina()
        raiz.add_widget(titulo_tela("Histórico", "Seus atendimentos por fazenda"))

        corpo = BoxLayout(orientation="vertical", padding=[dp(16), dp(8), dp(16),
                          dp(12)], spacing=dp(12))

        # --- Seletor de propriedade (vacas mostradas por fazenda) ---
        self.propriedade_selecionada = ""
        self.caixa_prop_hist = BoxLayout(orientation="vertical", size_hint_y=None,
                                         spacing=dp(6))
        self.caixa_prop_hist.bind(
            minimum_height=self.caixa_prop_hist.setter("height"))
        corpo.add_widget(self.caixa_prop_hist)

        # --- Filtro por nº da vaca ---
        linha_filtro = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.filtro = Campo(hint_text="Filtrar por nº da vaca", multiline=False)
        botao_filtrar = Botao(texto=rotulo_icone("lupa", ""), cor=CORES["verde"],
                              size_hint_x=None, width=dp(60), font_size="18sp")
        botao_filtrar.bind(on_release=lambda *_: self.carregar())
        linha_filtro.add_widget(self.filtro)
        linha_filtro.add_widget(botao_filtrar)
        corpo.add_widget(linha_filtro)

        # --- Lista rolável ---
        scroll = RolagemComCampos()
        self.lista = GridLayout(cols=1, size_hint_y=None, spacing=dp(10),
                                padding=(0, dp(2)))
        self.lista.bind(minimum_height=self.lista.setter("height"))
        scroll.add_widget(self.lista)
        corpo.add_widget(scroll)

        raiz.add_widget(corpo)
        self.add_widget(raiz)

    def on_pre_enter(self):
        if not self.propriedade_selecionada:
            self.propriedade_selecionada = self.servicos.sessao.propriedade
        self._montar_seletor_propriedades()
        self.carregar()

    def _montar_seletor_propriedades(self):
        self.caixa_prop_hist.clear_widgets()
        propriedades = self.servicos.propriedades.listar()
        if not propriedades:
            return
        if self.propriedade_selecionada not in propriedades:
            self.propriedade_selecionada = propriedades[0]
        self.caixa_prop_hist.add_widget(etiqueta("Fazenda"))
        self.seletor_prop_hist = SeletorOpcoes(
            propriedades[:8], cols=2, altura_linha=dp(38),
            valor_inicial=self.propriedade_selecionada,
            ao_selecionar=self._trocar_propriedade)
        self.caixa_prop_hist.add_widget(self.seletor_prop_hist)

    def _trocar_propriedade(self, nome):
        self.propriedade_selecionada = nome
        self.carregar()

    def carregar(self):
        """Histórico da fazenda selecionada, AGRUPADO por vaca: um card por vaca
        (com contagem), tocando abre a lista completa daquela vaca."""
        self.lista.clear_widgets()
        filtro = self.filtro.text.strip() or None
        atendimentos = self.servicos.atendimentos.listar(limite=500, id_vaca=filtro)
        if self.propriedade_selecionada:
            atendimentos = [a for a in atendimentos
                            if a.propriedade == self.propriedade_selecionada]
        if not atendimentos:
            vazio = Cartao(size_hint_y=None, height=dp(70))
            msg = ("Nenhum atendimento nesta fazenda ainda."
                   if self.propriedade_selecionada
                   else "Nenhum atendimento encontrado.")
            vazio.add_widget(texto_livre(msg, cor=CORES["texto_suave"],
                                         tamanho="14sp"))
            self.lista.add_widget(vazio)
            return

        grupos = {}
        ordem = []
        for a in atendimentos:  # já vem do mais recente para o mais antigo
            if a.id_vaca not in grupos:
                grupos[a.id_vaca] = []
                ordem.append(a.id_vaca)
            grupos[a.id_vaca].append(a)

        for id_vaca in ordem:
            self.lista.add_widget(self._cartao_vaca(id_vaca, grupos[id_vaca]))

    def _cartao_vaca(self, id_vaca, atendimentos):
        mais_recente = atendimentos[0]
        cartao = CartaoClicavel(size_hint_y=None, height=dp(96), padding=dp(14),
                                spacing=dp(6))
        cartao.bind(on_release=lambda *_: self._abrir_historico_vaca(
            id_vaca, atendimentos))

        topo = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        topo.add_widget(texto_livre("[b]%s Vaca %s[/b]" %
                                    (rotulo_icone("vaca", "").rstrip(), id_vaca),
                                    cor=CORES["texto"], tamanho="16sp",
                                    altura=dp(28)))
        topo.add_widget(Widget())
        if len(atendimentos) > 1:
            topo.add_widget(chip("%d registros" % len(atendimentos),
                                 CORES["chip_pend"], CORES["marrom"],
                                 icone_nome="prancheta"))
        elif mais_recente.sincronizado:
            topo.add_widget(chip("nuvem", CORES["chip_ok"], CORES["verde_escuro"],
                                 icone_nome="check_circulo"))
        else:
            topo.add_widget(chip("local", CORES["chip_pend"], CORES["marrom"],
                                 icone_nome="relogio"))
        cartao.add_widget(topo)

        proc = mais_recente.procedimento or "sem procedimento"
        cartao.add_widget(texto_livre("Último: %s" % proc, cor=CORES["verde"],
                                      tamanho="14sp", altura=dp(22), bold=True))

        rodape = "%s %s  ·  %s" % (mais_recente.data, mais_recente.hora,
                                   mais_recente.status_reprodutivo or "sem status")
        cartao.add_widget(texto_livre(rodape, cor=CORES["texto_suave"],
                                      tamanho="12sp", altura=dp(18)))
        return cartao

    def _abrir_historico_vaca(self, id_vaca, atendimentos):
        """Popup com TODOS os atendimentos daquela vaca, do mais recente ao
        mais antigo."""
        conteudo = BoxLayout(orientation="vertical", padding=dp(16),
                             spacing=dp(12))
        pintar_fundo(conteudo, CORES["fundo"], raio=18)

        conteudo.add_widget(texto_livre(
            "[b]%s Histórico completo — Vaca %s[/b]" %
            (rotulo_icone("vaca", "").rstrip(), id_vaca),
            cor=CORES["verde"], tamanho="16sp", altura=dp(46)))

        scroll = RolagemComCampos()
        grade = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grade.bind(minimum_height=grade.setter("height"))
        scroll.add_widget(grade)

        popup = Popup(title="", separator_height=0, content=conteudo,
                      size_hint=(0.94, 0.86), background="",
                      background_color=(0, 0, 0, 0.5))

        def recarregar_popup():
            restantes = self.servicos.atendimentos.listar(limite=200, id_vaca=id_vaca)
            if not restantes:
                popup.dismiss()
                self.carregar()
                return
            grade.clear_widgets()
            for a in restantes:
                grade.add_widget(self._linha_detalhe(a, recarregar_popup))

        for a in atendimentos:
            grade.add_widget(self._linha_detalhe(a, recarregar_popup))
        conteudo.add_widget(scroll)

        def excluir_tudo():
            confirmar(
                "Excluir vaca %s" % id_vaca,
                "Isso apaga TODOS os %d atendimento(s) desta vaca. "
                "Não dá para desfazer." % len(atendimentos),
                ao_confirmar=lambda: (
                    self.servicos.atendimentos.excluir_vaca(id_vaca),
                    popup.dismiss(), self.carregar()),
                texto_confirmar="Excluir tudo")

        linha_acoes = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(12))
        botao_excluir_vaca = Botao(
            texto=rotulo_icone("lixeira", "Excluir esta vaca"),
            cor=CORES["terracota"])
        botao_excluir_vaca.bind(on_release=lambda *_: excluir_tudo())
        botao_fechar = Botao(texto="Fechar", cor=CORES["marrom"])
        botao_fechar.bind(on_release=popup.dismiss)
        linha_acoes.add_widget(botao_excluir_vaca)
        linha_acoes.add_widget(botao_fechar)
        conteudo.add_widget(linha_acoes)

        popup.open()

    def _linha_detalhe(self, a, apos_excluir=None):
        cartao = Cartao(padding=dp(12), spacing=dp(4))

        marca = "nuvem" if a.sincronizado else "local"
        cor_marca = (CORES["chip_ok"], CORES["verde_escuro"]) if a.sincronizado \
            else (CORES["chip_pend"], CORES["marrom"])
        topo = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        topo.add_widget(texto_livre("[b]%s %s[/b]" % (a.data, a.hora),
                                    cor=CORES["texto"], tamanho="13sp",
                                    altura=dp(28)))
        topo.add_widget(Widget())
        topo.add_widget(chip(marca, cor_marca[0], cor_marca[1]))
        if apos_excluir is not None and a.id_banco is not None:
            botao_lixeira = Botao(texto=rotulo_icone("lixeira", ""),
                                  cor=CORES["terracota"], raio=10,
                                  size_hint=(None, None), width=dp(40),
                                  height=dp(28), font_size="15sp")

            def excluir_este(*_):
                confirmar(
                    "Excluir atendimento",
                    "Apagar este atendimento de %s %s? Não dá para desfazer."
                    % (a.data, a.hora),
                    ao_confirmar=lambda: (
                        self.servicos.atendimentos.excluir(a.id_banco),
                        apos_excluir()))
            botao_lixeira.bind(on_release=excluir_este)
            topo.add_widget(botao_lixeira)
        cartao.add_widget(topo)

        if a.procedimento:
            cartao.add_widget(texto_livre("[b]Procedimento:[/b] %s" % a.procedimento,
                                          cor=CORES["verde"], tamanho="12sp",
                                          altura=dp(18)))
        if a.status_reprodutivo:
            cartao.add_widget(texto_livre("[b]Status:[/b] %s" % a.status_reprodutivo,
                                          cor=CORES["texto_suave"], tamanho="12sp",
                                          altura=dp(18)))
        if a.diagnostico:
            cartao.add_widget(texto_livre("[b]Diagnóstico:[/b] %s" % a.diagnostico,
                                          cor=CORES["texto_suave"], tamanho="12sp",
                                          altura=dp(18)))
        if a.medicacoes:
            cartao.add_widget(texto_livre("[b]Medicações:[/b] %s" % a.medicacoes,
                                          cor=CORES["texto_suave"], tamanho="12sp",
                                          altura=dp(18)))
        return cartao
