"""
presentation/app.py — Aplicativo Kivy (Windows/Android).

É a "casca" da interface: monta o composition root (casos de uso), cria as telas
injetando `servicos`, cuida de ajustes de plataforma (teclado/permissões no
Android) e faz um backup do banco ao fechar. Nenhuma regra de negócio aqui.
"""

import os
import shutil
from datetime import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import FadeTransition, ScreenManager
from kivy.utils import platform

from vetvoice.composition import montar_servicos
from vetvoice.presentation.theme import CORES
from vetvoice.presentation.widgets import Botao, BottomNav, Cartao, texto_livre
from vetvoice.presentation.screens.atendimento import TelaAtendimento
from vetvoice.presentation.screens.configuracoes import TelaConfig
from vetvoice.presentation.screens.historico import TelaHistorico
from vetvoice.presentation.screens.inicial import TelaInicial
from vetvoice.presentation.screens.login import TelaLogin
from vetvoice.presentation.screens.splash import TelaSplash
from vetvoice.shared import config


class AppVeterinaria(App):
    ESPACO_MINIMO_BYTES = 20 * 1024 * 1024   # 20 MB de folga mínima
    MAX_BACKUPS_GUARDADOS = 5

    # Telas que exibem a barra de navegação inferior (as "abas" do app). As
    # demais (splash, login, atendimento) ocupam a tela cheia, sem a barra.
    ABAS = ("inicial", "historico", "config")

    def build(self):
        self.title = "VetVoice — Atendimento Veterinário"
        # Composition root: monta todos os casos de uso com as dependências reais.
        self.servicos = montar_servicos()

        Window.clearcolor = CORES["fundo"]
        if platform not in ("android", "ios"):
            Window.size = (400, 760)
            Window.minimum_width, Window.minimum_height = 360, 620

        if platform == "android":
            self._preparar_android()

        # Raiz = conteúdo (ScreenManager) + barra inferior fixa. A barra só
        # aparece nas abas; splash/login/atendimento ocupam tudo.
        self._raiz = BoxLayout(orientation="vertical")
        self._construir_conteudo(tela_inicial="splash")
        return self._raiz

    def _construir_conteudo(self, tela_inicial):
        """(Re)cria o ScreenManager e a barra inferior dentro da raiz. Usado no
        build e ao trocar de tema (que exige recriar os widgets com a paleta nova)."""
        self._raiz.clear_widgets()

        self.sm = ScreenManager(transition=FadeTransition(duration=0.18))
        self.sm.add_widget(TelaSplash(self.servicos, name="splash"))
        self.sm.add_widget(TelaLogin(self.servicos, name="login"))
        self.sm.add_widget(TelaInicial(self.servicos, name="inicial"))
        self.sm.add_widget(TelaAtendimento(self.servicos, name="atendimento"))
        self.sm.add_widget(TelaHistorico(self.servicos, name="historico"))
        self.sm.add_widget(TelaConfig(self.servicos, name="config"))
        self.sm.bind(current=self._ao_trocar_tela)

        self.nav = BottomNav(ao_selecionar=self._ir_para_aba)

        self._raiz.add_widget(self.sm)
        self._raiz.add_widget(self.nav)

        self.sm.current = tela_inicial
        self._ao_trocar_tela(self.sm, tela_inicial)

    def _ir_para_aba(self, nome):
        self.sm.current = nome

    def _ao_trocar_tela(self, _sm, nome):
        """Mostra a barra inferior só nas abas; destaca a aba atual."""
        eh_aba = nome in self.ABAS
        self.nav.set_ativo(nome if eh_aba else "")
        self.nav.height = dp(62) if eh_aba else 0
        self.nav.opacity = 1 if eh_aba else 0
        self.nav.disabled = not eh_aba

    def reconstruir_telas(self, tela_atual="config"):
        """Recria as telas para pegarem as cores atuais (o tema é 'queimado' nos
        widgets ao desenhar, então trocar de tema exige reconstruir)."""
        self._construir_conteudo(tela_inicial=tela_atual)

    def _preparar_android(self):
        """Ajustes só do celular: reposicionar a tela quando o teclado abre e
        pedir a permissão de microfone em tempo de execução."""
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET])
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # BACKUP AUTOMÁTICO AO FECHAR (cópia extra do banco, além do save no toque)
    # -----------------------------------------------------------------------
    def on_request_close(self, *args, **kwargs):
        ok, motivo = self._fazer_backup_seguro()
        if not ok:
            self._avisar_espaco_insuficiente(motivo)
            return True  # segura o fechamento até o usuário decidir
        return False

    def _fazer_backup_seguro(self):
        if not os.path.isfile(config.DATABASE_PATH):
            return True, None
        try:
            espaco_livre = shutil.disk_usage(config.DATA_DIR).free
        except OSError:
            espaco_livre = None

        if espaco_livre is not None and espaco_livre < self.ESPACO_MINIMO_BYTES:
            livre_mb = espaco_livre / (1024 * 1024)
            return False, ("Restam apenas %.1f MB livres no armazenamento. "
                           "Seus atendimentos já salvos continuam no aparelho, "
                           "mas a cópia de segurança (backup) não será feita "
                           "agora." % livre_mb)
        try:
            pasta_backups = os.path.join(config.DATA_DIR, "backups")
            os.makedirs(pasta_backups, exist_ok=True)
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = os.path.join(pasta_backups, "atendimentos_%s.db" % carimbo)
            shutil.copy2(config.DATABASE_PATH, destino)
            self._limpar_backups_antigos(pasta_backups)
            return True, None
        except OSError as erro:
            return False, ("Não foi possível salvar a cópia de segurança "
                           "(%s). Seus atendimentos já salvos continuam no "
                           "aparelho normalmente." % erro)

    def _limpar_backups_antigos(self, pasta_backups):
        arquivos = sorted(
            (f for f in os.listdir(pasta_backups) if f.endswith(".db")),
            reverse=True)
        for antigo in arquivos[self.MAX_BACKUPS_GUARDADOS:]:
            try:
                os.remove(os.path.join(pasta_backups, antigo))
            except OSError:
                pass

    def _avisar_espaco_insuficiente(self, motivo):
        conteudo = Cartao(padding=dp(18), spacing=dp(14))
        conteudo.add_widget(texto_livre("[b]Pouco espaço de armazenamento[/b]",
                                        cor=CORES["terracota"], tamanho="16sp",
                                        altura=dp(26)))
        aviso_texto = texto_livre(motivo, cor=CORES["texto"], tamanho="13sp")
        aviso_texto.valign = "top"
        conteudo.add_widget(aviso_texto)

        linha_botoes = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        botao_cancelar = Botao(texto="Cancelar", cor=CORES["cartao"],
                               cor_texto=CORES["texto_suave"], borda=CORES["borda"])
        botao_fechar = Botao(texto="Fechar mesmo assim", cor=CORES["terracota"])
        linha_botoes.add_widget(botao_cancelar)
        linha_botoes.add_widget(botao_fechar)
        conteudo.add_widget(linha_botoes)

        popup = Popup(title="", separator_height=0, content=conteudo,
                      size_hint=(0.88, 0.42), background="",
                      background_color=(0, 0, 0, 0.55), auto_dismiss=False)
        botao_cancelar.bind(on_release=popup.dismiss)

        def fechar_mesmo_assim(*_):
            popup.dismiss()
            self.stop()

        botao_fechar.bind(on_release=fechar_mesmo_assim)
        popup.open()
