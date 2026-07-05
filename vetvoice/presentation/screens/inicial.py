"""
screens/inicial.py — Tela inicial (aba Início): saudação + status de sync, um
cartão-herói de gravação por voz, o cartão da jornada (propriedade + tipo) e a
ação principal. Navegação entre abas fica na barra inferior.
"""

from datetime import datetime

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from vetvoice.presentation.dialogs import aviso, confirmar
from vetvoice.presentation.gravacao import alternar_gravacao
from vetvoice.presentation.theme import CORES, pintar_fundo, rotulo_icone
from vetvoice.presentation.widgets import (
    Botao, Campo, Cartao, ControleGravacao, RolagemComCampos, SeletorOpcoes,
    etiqueta, pagina, texto_livre,
)
from vetvoice.shared import config


def _saudacao() -> str:
    h = datetime.now().hour
    if h < 12:
        return "Bom dia"
    if h < 18:
        return "Boa tarde"
    return "Boa noite"


class TelaInicial(Screen):
    def __init__(self, servicos, **kwargs):
        self.servicos = servicos
        super().__init__(**kwargs)
        raiz = pagina()

        scroll = RolagemComCampos()
        corpo = BoxLayout(orientation="vertical", padding=[dp(18), dp(16), dp(18),
                          dp(20)], spacing=dp(14), size_hint_y=None)
        corpo.bind(minimum_height=corpo.setter("height"))

        # --- Saudação + status de sincronização (pílula tocável) ---
        cabeca = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        saud = BoxLayout(orientation="vertical", spacing=dp(1))
        self.lbl_saudacao = texto_livre(_saudacao(), cor=CORES["texto_suave"],
                                        tamanho="13sp", altura=dp(18))
        self.lbl_usuario = texto_livre("[b]Veterinário[/b]", cor=CORES["texto"],
                                       tamanho="19sp", altura=dp(28))
        saud.add_widget(self.lbl_saudacao)
        saud.add_widget(self.lbl_usuario)
        cabeca.add_widget(saud)
        cabeca.add_widget(Widget())
        self.botao_sync = Botao(texto="", cor=CORES["chip_ok"],
                                cor_texto=CORES["verde_escuro"], raio=15,
                                size_hint=(None, None), height=dp(34),
                                width=dp(150), font_size="12sp")
        self.botao_sync.bind(on_release=self.sincronizar)
        cabeca.add_widget(self.botao_sync)
        corpo.add_widget(cabeca)

        # --- Cartão-herói: gravar e ditar o atendimento ---
        hero = Cartao(padding=[dp(16), dp(20)], spacing=dp(6))
        hero.add_widget(texto_livre("Toque e dite o atendimento",
                                    cor=CORES["texto_suave"], tamanho="14sp",
                                    altura=dp(22)))
        centro = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(112))
        self.botao_gravar_nota = ControleGravacao(
            ao_tocar=self.gravar_nota,
            rotulo=rotulo_icone("estrelas", "FALAR E PREENCHER"))
        centro.add_widget(self.botao_gravar_nota)
        hero.add_widget(centro)
        self.nota_transcricao = Campo(
            hint_text="A fala aparece aqui — ou digite um comando",
            size_hint_y=None, height=dp(64))
        hero.add_widget(self.nota_transcricao)
        botao_interpretar = Botao(
            texto=rotulo_icone("estrelas", "Preencher e abrir atendimento"),
            cor=CORES["verde_claro"], size_hint_y=None, height=dp(48),
            font_size="14sp")
        botao_interpretar.bind(on_release=self.interpretar_comando)
        hero.add_widget(botao_interpretar)
        corpo.add_widget(hero)

        # --- Cartão: jornada de hoje (propriedade + tipo de produção) ---
        dados = Cartao()
        dados.add_widget(texto_livre("[b]Jornada de hoje[/b]", cor=CORES["texto"],
                                     tamanho="15sp", altura=dp(24)))

        dados.add_widget(etiqueta("Propriedade / Fazenda"))
        linha_prop = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.campo_propriedade = Campo(multiline=False,
                                       hint_text="Ex: Fazenda Boa Vista")
        self.seletor_propriedades = None
        self.campo_propriedade.bind(text=self._ao_editar_propriedade_manual)
        botao_add_prop = Botao(texto=rotulo_icone("salvar", "Add"),
                               cor=CORES["verde_claro"], size_hint_x=None,
                               width=dp(92), font_size="13sp")
        botao_add_prop.bind(on_release=lambda *_: self._adicionar_propriedade())
        linha_prop.add_widget(self.campo_propriedade)
        linha_prop.add_widget(botao_add_prop)
        dados.add_widget(linha_prop)

        self.caixa_propriedades_salvas = BoxLayout(orientation="vertical",
                                                   size_hint_y=None, spacing=dp(6))
        self.caixa_propriedades_salvas.bind(
            minimum_height=self.caixa_propriedades_salvas.setter("height"))
        dados.add_widget(self.caixa_propriedades_salvas)

        dados.add_widget(etiqueta("Tipo de Produção"))
        self.seletor_tipo = SeletorOpcoes(
            config.TIPO_PRODUCAO_OPCOES,
            valor_inicial=self.servicos.sessao.tipo_producao)
        dados.add_widget(self.seletor_tipo)
        corpo.add_widget(dados)

        # --- Ação principal ---
        botao_iniciar = Botao(
            texto=rotulo_icone("estetoscopio", "Iniciar atendimento"),
            cor=CORES["verde"], size_hint_y=None, height=dp(56), font_size="17sp")
        botao_iniciar.bind(on_release=self.iniciar)
        corpo.add_widget(botao_iniciar)

        scroll.add_widget(corpo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def on_pre_enter(self):
        sessao = self.servicos.sessao
        self.lbl_saudacao.text = _saudacao()
        self.lbl_usuario.text = "[b]%s[/b]" % (sessao.usuario or "Veterinário")
        self.campo_propriedade.text = sessao.propriedade
        self.seletor_tipo.selecionar(sessao.tipo_producao, disparar_callback=False)
        self._atualizar_propriedades_salvas()
        self._atualizar_status_sync()

    def _atualizar_status_sync(self):
        pendentes = self.servicos.atendimentos.contar_pendentes()
        if pendentes:
            self.botao_sync.text = rotulo_icone(
                "nuvem_subir", "%d p/ enviar" % pendentes)
            self.botao_sync._cor = CORES["chip_pend"]
            self.botao_sync._c.rgba = CORES["chip_pend"]
            self.botao_sync.color = CORES["marrom"]
        else:
            self.botao_sync.text = rotulo_icone("check_circulo", "Sincronizado")
            self.botao_sync._cor = CORES["chip_ok"]
            self.botao_sync._c.rgba = CORES["chip_ok"]
            self.botao_sync.color = CORES["verde_escuro"]

    def _atualizar_propriedades_salvas(self):
        self.caixa_propriedades_salvas.clear_widgets()
        salvas = self.servicos.propriedades.listar()
        if not salvas:
            self.seletor_propriedades = None
            return
        self.caixa_propriedades_salvas.add_widget(
            etiqueta("Ou toque numa já usada"))
        texto_atual = self.campo_propriedade.text.strip()
        self.seletor_propriedades = SeletorOpcoes(
            salvas[:8], cols=2, altura_linha=dp(38),
            valor_inicial=texto_atual if texto_atual in salvas else "",
            ao_selecionar=self._escolher_propriedade)
        self.caixa_propriedades_salvas.add_widget(self.seletor_propriedades)

        botao_gerenciar = Botao(
            texto=rotulo_icone("lixeira", "Gerenciar fazendas"),
            cor=CORES["cartao"], cor_texto=CORES["texto_suave"],
            borda=CORES["borda"], size_hint_y=None, height=dp(38),
            font_size="13sp")
        botao_gerenciar.bind(on_release=lambda *_: self._gerenciar_propriedades())
        self.caixa_propriedades_salvas.add_widget(botao_gerenciar)

    def _gerenciar_propriedades(self):
        """Popup que lista as fazendas com um botão de lixeira em cada. Excluir
        uma fazenda apaga TODOS os atendimentos dela."""
        salvas = self.servicos.propriedades.listar()
        conteudo = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        pintar_fundo(conteudo, CORES["fundo"], raio=18)
        conteudo.add_widget(texto_livre(
            "[b]Gerenciar fazendas[/b]", cor=CORES["verde"],
            tamanho="16sp", altura=dp(30)))
        conteudo.add_widget(texto_livre(
            "Excluir uma fazenda apaga todos os atendimentos dela.",
            cor=CORES["texto_suave"], tamanho="12sp", altura=dp(34)))

        scroll = RolagemComCampos()
        grade = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        grade.bind(minimum_height=grade.setter("height"))
        scroll.add_widget(grade)
        conteudo.add_widget(scroll)

        botao_fechar = Botao(texto="Fechar", cor=CORES["marrom"],
                             size_hint_y=None, height=dp(46))
        conteudo.add_widget(botao_fechar)

        popup = Popup(title="", separator_height=0, content=conteudo,
                      size_hint=(0.9, 0.8), background="",
                      background_color=(0, 0, 0, 0.5))
        botao_fechar.bind(on_release=popup.dismiss)
        popup.bind(on_dismiss=lambda *_: self._atualizar_propriedades_salvas())

        def recarregar():
            restantes = self.servicos.propriedades.listar()
            grade.clear_widgets()
            if not restantes:
                vazio = Cartao(size_hint_y=None, height=dp(64))
                vazio.add_widget(texto_livre(
                    "Nenhuma fazenda salva.", cor=CORES["texto_suave"],
                    tamanho="13sp"))
                grade.add_widget(vazio)
                return
            for nome in restantes:
                grade.add_widget(self._linha_propriedade(nome, recarregar))

        def _construir():
            grade.clear_widgets()
            if not salvas:
                vazio = Cartao(size_hint_y=None, height=dp(64))
                vazio.add_widget(texto_livre(
                    "Nenhuma fazenda salva.", cor=CORES["texto_suave"],
                    tamanho="13sp"))
                grade.add_widget(vazio)
            else:
                for nome in salvas:
                    grade.add_widget(self._linha_propriedade(nome, recarregar))
        _construir()
        popup.open()

    def _linha_propriedade(self, nome, apos_excluir):
        cartao = Cartao(orientation="horizontal", size_hint_y=None, height=dp(56),
                        padding=dp(12), spacing=dp(10))
        rotulo = texto_livre("[b]%s[/b]" % nome, cor=CORES["texto"],
                             tamanho="14sp")
        cartao.add_widget(rotulo)
        botao_lixeira = Botao(texto=rotulo_icone("lixeira", ""),
                              cor=CORES["terracota"], raio=10,
                              size_hint=(None, None), width=dp(48),
                              height=dp(36), font_size="16sp")

        def excluir(*_):
            confirmar(
                "Excluir fazenda",
                "Apagar a fazenda \"%s\" e TODOS os atendimentos dela? "
                "Não dá para desfazer." % nome,
                ao_confirmar=lambda: (
                    self.servicos.propriedades.excluir(nome),
                    self._limpar_campo_se_igual(nome), apos_excluir()))
        botao_lixeira.bind(on_release=excluir)
        cartao.add_widget(botao_lixeira)
        return cartao

    def _limpar_campo_se_igual(self, nome):
        if self.campo_propriedade.text.strip() == nome:
            self.campo_propriedade.text = ""

    def gravar_nota(self, *_):
        alternar_gravacao(self.servicos, self, self.botao_gravar_nota,
                          self.nota_transcricao)

    def interpretar_comando(self, *_):
        """Interpreta a fala como um COMANDO completo e já abre o Atendimento
        preenchido (define propriedade, vaca e campos)."""
        texto = self.nota_transcricao.text.strip()
        if not texto:
            aviso("Atenção", "Fale (ou digite) o comando antes de preencher.")
            return

        dados = self.servicos.analise.analisar(texto)

        propriedade_dita = (dados.get("propriedade") or "").strip()
        if propriedade_dita:
            self.campo_propriedade.text = propriedade_dita
            self.servicos.propriedades.adicionar(propriedade_dita)
            self._atualizar_propriedades_salvas()

        propriedade = self.campo_propriedade.text.strip()
        if not propriedade:
            aviso("Falta a propriedade",
                  "Não identifiquei a fazenda no comando. Diga algo como "
                  "\"cabanha Boa Vista...\" ou escreva o nome no campo "
                  "Propriedade antes de preencher.")
            return

        sessao = self.servicos.sessao
        sessao.propriedade = propriedade
        sessao.tipo_producao = self.seletor_tipo.valor
        sessao.prefill_comando = texto
        self.ir("atendimento")

    def on_leave(self):
        sessao = getattr(self, "_sessao_audio", None)
        if sessao is not None:
            try:
                sessao.cancelar()
            except Exception:
                pass
            self._sessao_audio = None

    def _adicionar_propriedade(self):
        nome = self.campo_propriedade.text.strip()
        if not nome:
            aviso("Atenção", "Escreva o nome da propriedade antes de adicionar.")
            return
        self.servicos.propriedades.adicionar(nome)
        self._atualizar_propriedades_salvas()
        if self.seletor_propriedades and nome in self.seletor_propriedades._botoes:
            self.seletor_propriedades.selecionar(nome, disparar_callback=False)

    def _escolher_propriedade(self, nome):
        self.campo_propriedade.text = nome

    def _ao_editar_propriedade_manual(self, _widget, texto):
        seletor = getattr(self, "seletor_propriedades", None)
        if seletor is None:
            return
        texto = texto.strip()
        if texto in seletor._botoes and seletor.valor != texto:
            seletor.selecionar(texto, disparar_callback=False)
        elif texto not in seletor._botoes and seletor.valor != "":
            seletor.selecionar("", disparar_callback=False)

    def iniciar(self, *_):
        if not self.campo_propriedade.text.strip():
            aviso("Atenção", "Informe o nome da propriedade para começar.")
            return
        sessao = self.servicos.sessao
        sessao.propriedade = self.campo_propriedade.text.strip()
        sessao.tipo_producao = self.seletor_tipo.valor
        self.ir("atendimento")

    def sincronizar(self, *_):
        resultado = self.servicos.sincronizacao.executar(
            self.campo_propriedade.text.strip() or "SemNome")
        if resultado.get("modo") == "simulado":
            aviso("Sincronização (modo local)",
                  "Marquei %s atendimento(s) como sincronizados neste "
                  "aparelho.\n\nPara enviar de verdade a uma planilha no seu "
                  "Google Drive, entre com o Google (aba Ajustes)."
                  % resultado["enviados"])
        elif resultado.get("erros"):
            aviso("Sincronização",
                  "Não consegui enviar agora.\n\n%s"
                  % resultado.get("detalhe", "Tente novamente."))
        else:
            corpo = ("Enviados: %s\nErros: %s" %
                     (resultado["enviados"], resultado["erros"]))
            if resultado.get("link"):
                corpo += "\n\nPlanilha no seu Drive:\n%s" % resultado["link"]
            aviso("Sincronizado com o Google", corpo)
        self._atualizar_status_sync()

    def ir(self, destino):
        self.manager.current = destino
