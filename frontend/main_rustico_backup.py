"""
main.py (frontend)
------------------
Interface gráfica do app, feita em Kivy. Roda no Windows (vira .exe) e no
Android (vira APK), usando o MESMO código.

Como rodar no computador (modo teste):
    pip install kivy SpeechRecognition
    python -m frontend.main

Telas:
    1. Inicial       -> nome da fazenda + do veterinário, status online, sincronizar
    2. Atendimento   -> id da vaca, botão gravar, campos preenchidos pela IA, salvar
    3. Histórico     -> últimos atendimentos, filtro por vaca
    4. Configurações -> informações e ajuda
"""

import threading

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp

from backend import database, audio_processor, ai_analyzer, google_sheets_sync
from backend.models import Atendimento
from backend.config import COLUNAS_EXIBICAO


# Guarda dados da sessão atual (fazenda e veterinário) para não repetir digitação
SESSAO = {"propriedade": "", "veterinario": ""}


# ===========================================================================
# COMPONENTES AUXILIARES
# ===========================================================================
def rotulo(texto, **kwargs):
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", dp(30))
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    lbl = Label(text=texto, **kwargs)
    lbl.bind(size=lbl.setter("text_size"))
    return lbl


def aviso(titulo, mensagem):
    """Mostra uma janelinha de aviso."""
    conteudo = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
    conteudo.add_widget(Label(text=mensagem))
    botao = Button(text="OK", size_hint_y=None, height=dp(44))
    conteudo.add_widget(botao)
    popup = Popup(title=titulo, content=conteudo, size_hint=(0.8, 0.4))
    botao.bind(on_release=popup.dismiss)
    popup.open()


# ===========================================================================
# TELA 1 — INICIAL
# ===========================================================================
class TelaInicial(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))

        layout.add_widget(Label(text="[b]Atendimento Veterinário[/b]", markup=True,
                                font_size="24sp", size_hint_y=None, height=dp(50)))

        layout.add_widget(rotulo("Nome da Propriedade / Fazenda:"))
        self.campo_propriedade = TextInput(multiline=False, size_hint_y=None,
                                            height=dp(44))
        layout.add_widget(self.campo_propriedade)

        layout.add_widget(rotulo("Nome do Veterinário:"))
        self.campo_veterinario = TextInput(multiline=False, size_hint_y=None,
                                            height=dp(44))
        layout.add_widget(self.campo_veterinario)

        self.status = rotulo("", height=dp(30))
        layout.add_widget(self.status)

        botao_iniciar = Button(text="Iniciar Atendimento", size_hint_y=None,
                               height=dp(56), background_color=(0.2, 0.6, 0.3, 1))
        botao_iniciar.bind(on_release=self.iniciar)
        layout.add_widget(botao_iniciar)

        botao_historico = Button(text="Ver Histórico", size_hint_y=None,
                                 height=dp(48))
        botao_historico.bind(on_release=lambda x: self.ir("historico"))
        layout.add_widget(botao_historico)

        botao_sincronizar = Button(text="Sincronizar com a Nuvem", size_hint_y=None,
                                   height=dp(48), background_color=(0.2, 0.4, 0.7, 1))
        botao_sincronizar.bind(on_release=self.sincronizar)
        layout.add_widget(botao_sincronizar)

        botao_config = Button(text="Configurações / Ajuda", size_hint_y=None,
                              height=dp(44))
        botao_config.bind(on_release=lambda x: self.ir("config"))
        layout.add_widget(botao_config)

        self.add_widget(layout)

    def on_pre_enter(self):
        self.campo_propriedade.text = SESSAO["propriedade"]
        self.campo_veterinario.text = SESSAO["veterinario"]
        pendentes = len(database.listar_nao_sincronizados())
        self.status.text = f"Registros aguardando sincronização: {pendentes}"

    def iniciar(self, *_):
        if not self.campo_propriedade.text.strip():
            aviso("Atenção", "Informe o nome da propriedade.")
            return
        SESSAO["propriedade"] = self.campo_propriedade.text.strip()
        SESSAO["veterinario"] = self.campo_veterinario.text.strip()
        self.ir("atendimento")

    def sincronizar(self, *_):
        resultado = google_sheets_sync.sincronizar(
            self.campo_propriedade.text.strip() or "SemNome"
        )
        modo = "simulada (modo teste)" if resultado["modo"] == "simulado" else "real"
        aviso("Sincronização",
              f"Sincronização {modo}.\n"
              f"Enviados: {resultado['enviados']}\nErros: {resultado['erros']}")
        self.on_pre_enter()

    def ir(self, destino):
        self.manager.current = destino


# ===========================================================================
# TELA 2 — ATENDIMENTO
# ===========================================================================
class TelaAtendimento(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))

        raiz.add_widget(Label(text="[b]Novo Atendimento[/b]", markup=True,
                              font_size="20sp", size_hint_y=None, height=dp(40)))

        # ID da vaca + botão gravar
        linha_topo = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        linha_topo.add_widget(rotulo("Vaca (brinco):", size_hint_x=0.4))
        self.campo_id = TextInput(multiline=False, hint_text="ex: 123")
        linha_topo.add_widget(self.campo_id)
        raiz.add_widget(linha_topo)

        self.botao_gravar = Button(text="🎤 GRAVAR E FALAR", size_hint_y=None,
                                   height=dp(64), font_size="18sp",
                                   background_color=(0.8, 0.2, 0.2, 1))
        self.botao_gravar.bind(on_release=self.gravar)
        raiz.add_widget(self.botao_gravar)

        self.transcricao = TextInput(hint_text="A fala transcrita aparece aqui "
                                     "(ou digite manualmente para testar)",
                                     size_hint_y=None, height=dp(70))
        raiz.add_widget(self.transcricao)

        botao_analisar = Button(text="Preencher campos a partir da fala",
                                size_hint_y=None, height=dp(44),
                                background_color=(0.2, 0.5, 0.7, 1))
        botao_analisar.bind(on_release=self.analisar_texto)
        raiz.add_widget(botao_analisar)

        # Área rolável com os campos editáveis
        scroll = ScrollView()
        self.grade = GridLayout(cols=1, size_hint_y=None, spacing=dp(4),
                                padding=(0, dp(6)))
        self.grade.bind(minimum_height=self.grade.setter("height"))
        scroll.add_widget(self.grade)
        raiz.add_widget(scroll)

        self.campos = {}
        for chave in ["procedimento", "raca", "peso_kg", "idade_anos",
                      "status_reprodutivo", "diagnostico", "medicacoes",
                      "proxima_acao", "observacoes"]:
            self.grade.add_widget(rotulo(COLUNAS_EXIBICAO[chave] + ":",
                                         height=dp(24)))
            entrada = TextInput(multiline=(chave in ("diagnostico", "observacoes")),
                                size_hint_y=None,
                                height=dp(60) if chave in ("diagnostico",
                                                           "observacoes") else dp(40))
            self.campos[chave] = entrada
            self.grade.add_widget(entrada)

        # Botões inferiores
        rodape = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        botao_salvar = Button(text="Salvar", background_color=(0.2, 0.6, 0.3, 1))
        botao_salvar.bind(on_release=self.salvar)
        botao_voltar = Button(text="Voltar")
        botao_voltar.bind(on_release=lambda x: setattr(self.manager,
                                                       "current", "inicial"))
        rodape.add_widget(botao_voltar)
        rodape.add_widget(botao_salvar)
        raiz.add_widget(rodape)

        self.add_widget(raiz)

    def on_pre_enter(self):
        # Limpa a tela para um novo atendimento
        self.campo_id.text = ""
        self.transcricao.text = ""
        for entrada in self.campos.values():
            entrada.text = ""

    def gravar(self, *_):
        self.botao_gravar.text = "🎧 Ouvindo... fale agora"
        self.botao_gravar.disabled = True

        def tarefa():
            texto = audio_processor.transcrever_do_microfone()

            def atualizar(*_):
                self.botao_gravar.text = "🎤 GRAVAR E FALAR"
                self.botao_gravar.disabled = False
                if texto:
                    self.transcricao.text = texto
                    self.analisar_texto()
                else:
                    aviso("Áudio", "Não consegui captar. Você pode digitar "
                          "a frase manualmente e clicar em 'Preencher campos'.")

            Clock.schedule_once(atualizar)

        threading.Thread(target=tarefa, daemon=True).start()

    def analisar_texto(self, *_):
        texto = self.transcricao.text.strip()
        if not texto:
            aviso("Atenção", "Não há texto para analisar.")
            return
        campos = ai_analyzer.analisar(texto)
        if campos.get("id_vaca") and not self.campo_id.text.strip():
            self.campo_id.text = campos["id_vaca"]
        for chave, entrada in self.campos.items():
            if campos.get(chave):
                entrada.text = campos[chave]

    def salvar(self, *_):
        if not self.campo_id.text.strip():
            aviso("Atenção", "Informe o número do brinco da vaca.")
            return
        atendimento = Atendimento(
            id_vaca=self.campo_id.text.strip(),
            veterinario=SESSAO["veterinario"],
            propriedade=SESSAO["propriedade"],
            transcricao_original=self.transcricao.text.strip(),
        )
        for chave, entrada in self.campos.items():
            setattr(atendimento, chave, entrada.text.strip())
        atendimento.preencher_data_hora()
        database.salvar_atendimento(atendimento)
        aviso("Salvo", f"Atendimento da vaca {atendimento.id_vaca} salvo!\n"
              "Será enviado à nuvem na próxima sincronização.")
        self.on_pre_enter()


# ===========================================================================
# TELA 3 — HISTÓRICO
# ===========================================================================
class TelaHistorico(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        raiz.add_widget(Label(text="[b]Histórico de Atendimentos[/b]", markup=True,
                              font_size="20sp", size_hint_y=None, height=dp(40)))

        linha_filtro = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.filtro = TextInput(hint_text="Filtrar por nº da vaca", multiline=False)
        botao_filtrar = Button(text="Filtrar", size_hint_x=0.3)
        botao_filtrar.bind(on_release=lambda x: self.carregar())
        linha_filtro.add_widget(self.filtro)
        linha_filtro.add_widget(botao_filtrar)
        raiz.add_widget(linha_filtro)

        scroll = ScrollView()
        self.lista = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        self.lista.bind(minimum_height=self.lista.setter("height"))
        scroll.add_widget(self.lista)
        raiz.add_widget(scroll)

        botao_voltar = Button(text="Voltar", size_hint_y=None, height=dp(48))
        botao_voltar.bind(on_release=lambda x: setattr(self.manager,
                                                       "current", "inicial"))
        raiz.add_widget(botao_voltar)

        self.add_widget(raiz)

    def on_pre_enter(self):
        self.carregar()

    def carregar(self):
        self.lista.clear_widgets()
        filtro = self.filtro.text.strip() or None
        atendimentos = database.listar_atendimentos(limite=50, id_vaca=filtro)
        if not atendimentos:
            self.lista.add_widget(rotulo("Nenhum atendimento encontrado.",
                                         height=dp(40)))
            return
        for a in atendimentos:
            marca = "✅" if a.sincronizado else "⏳"
            texto = (f"{marca} Vaca {a.id_vaca} — {a.procedimento or 'sem proc.'}\n"
                     f"    {a.data} {a.hora} | {a.status_reprodutivo}")
            item = Label(text=texto, markup=True, size_hint_y=None, height=dp(60),
                         halign="left", valign="middle")
            item.bind(size=item.setter("text_size"))
            self.lista.add_widget(item)


# ===========================================================================
# TELA 4 — CONFIGURAÇÕES / AJUDA
# ===========================================================================
class TelaConfig(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        raiz.add_widget(Label(text="[b]Configurações e Ajuda[/b]", markup=True,
                              font_size="20sp", size_hint_y=None, height=dp(40)))

        texto_ajuda = (
            "MODO DE TESTE (atual): gratuito e offline.\n"
            "- Transcrição pelo reconhecimento gratuito do Google Web.\n"
            "- Preenchimento por regras locais em português.\n"
            "- Dados salvos apenas neste aparelho (SQLite).\n\n"
            "PARA ATIVAR A NUVEM (opcional, avançado):\n"
            "Abra o arquivo backend/config.py e mude para True:\n"
            "  USAR_GOOGLE_CLOUD_SPEECH  (transcrição paga, mais precisa)\n"
            "  USAR_IA_OPENAI            (análise com GPT)\n"
            "  USAR_GOOGLE_SHEETS        (envio para planilha na nuvem)\n"
            "Depois coloque as credenciais na pasta 'credenciais/'.\n\n"
            "Dica: se o microfone não funcionar, basta digitar a frase\n"
            "no campo de transcrição e tocar em 'Preencher campos'."
        )
        scroll = ScrollView()
        lbl = Label(text=texto_ajuda, size_hint_y=None, halign="left",
                    valign="top")
        lbl.bind(size=lbl.setter("text_size"),
                 texture_size=lambda i, v: setattr(lbl, "height", v[1]))
        scroll.add_widget(lbl)
        raiz.add_widget(scroll)

        botao_voltar = Button(text="Voltar", size_hint_y=None, height=dp(48))
        botao_voltar.bind(on_release=lambda x: setattr(self.manager,
                                                       "current", "inicial"))
        raiz.add_widget(botao_voltar)
        self.add_widget(raiz)


# ===========================================================================
# APLICATIVO PRINCIPAL
# ===========================================================================
class AppVeterinaria(App):
    def build(self):
        self.title = "Atendimento Veterinário"
        database.inicializar_banco()   # garante que o banco existe

        gerenciador = ScreenManager()
        gerenciador.add_widget(TelaInicial(name="inicial"))
        gerenciador.add_widget(TelaAtendimento(name="atendimento"))
        gerenciador.add_widget(TelaHistorico(name="historico"))
        gerenciador.add_widget(TelaConfig(name="config"))
        return gerenciador


if __name__ == "__main__":
    AppVeterinaria().run()
