# 🐄 VetVoice — Atendimento Veterinário por Voz

O VetVoice é um aplicativo Android (feito em Python/Kivy) para o veterinário de
campo registrar atendimentos de bovinos **falando**, sem digitar no meio do
curral. Ele transcreve a fala, separa os dados em campos (animal, procedimento,
diagnóstico, medicação...), guarda tudo **offline** no aparelho e, quando o
veterinário quiser, envia para uma **planilha Google Sheets no Drive dele**.

---

## 🎯 Princípios do aplicativo

1. **Mão livre, olho no animal.** Tudo que dá para falar, se fala. A digitação
   é sempre um plano B, nunca uma exigência.
2. **Offline primeiro.** Fazenda não tem sinal garantido. Tudo é salvo no
   SQLite local na hora; a nuvem é sincronização, não dependência.
3. **A gravação só para quando EU mandar.** O microfone não se desliga sozinho
   por silêncio — pausas fazem parte do trabalho de campo. Toca para gravar,
   toca para parar.
4. **Cada cliente é dono dos seus dados.** O login com Google é feito na conta
   de CADA usuário; a planilha é criada no Drive DELE. Nada passa por um
   servidor central.
5. **Interface de dedo grosso e luva.** Botões grandes, chips tocáveis, rolagem
   que funciona começando de qualquer lugar da tela — inclusive em cima de um
   botão.
6. **Nunca perder um atendimento.** Backup automático do banco ao pausar e ao
   fechar; a Ronda ainda salva um `.txt` bruto de segurança antes de processar.

---

## 📱 O que o app faz (telas)

| Tela | Função |
|------|--------|
| **Login** | Nome simples (modo local) ou **Entrar com Google** (nuvem). |
| **Início** | Saudação, status de sincronização, ditado rápido ("Falar e preencher"), escolha da fazenda e tipo de produção, botões **Iniciar atendimento** e **Nova ronda**. |
| **Atendimento** | Ficha de um animal: gravação por voz contínua, campos com chips (raça, procedimento, diagnóstico) editáveis pelo chip **"Outro"**, salvar. |
| **Nova Ronda** | Abre **já gravando** com um botão grande. O veterinário percorre a fazenda falando `"vaca 12 ... vaca 15 ..."`. Ao tocar para parar: salva `.txt` de segurança, separa por animal, cria um atendimento por animal e tenta sincronizar com a planilha — tudo automático. |
| **Histórico** | Lista/filtra atendimentos, edita, exclui, sincroniza. |
| **Ajustes** | Conta Google, tema, gestão de fazendas e dos **termos criados pelo usuário** (dicionários editáveis). |

### Frases que o app entende (parser híbrido de regras em português)

- `"Vaca 123, feita inseminação artificial, animal vazia"`
- `"Vaca 321, diagnóstico de gestação, implantado chip hormonal, gestante"`
- `"Vaca 104, cetose subclínica, tratamento com propileno glicol"`

Na **Ronda**, os marcadores `vaca/brinco/animal/número N` separam a fala de
cada animal automaticamente (`vetvoice/domain/parsing/segmentacao.py`).

---

## 🔑 Login com Google — como funciona (e o que foi corrigido)

O login usa **OAuth 2.0 com PKCE** (fluxo loopback padrão do Google, sem
bibliotecas externas): o app abre o navegador, o usuário autoriza na conta
Google **dele**, e o navegador devolve o código para o app pela porta local
`http://127.0.0.1`.

**A "tela preta" ao logar (corrigida):** apps Kivy no Android são **mortos
pelo sistema** ao ir para segundo plano se o `App` não tiver `on_pause`
retornando `True`. Abrir o navegador para o login pausava o app → o Android o
matava → ao voltar, tela preta e login perdido. A correção está em
`vetvoice/presentation/app.py` (`on_pause`/`on_resume`). Sem esse método, o
sintoma volta — **não remover**.

**Plano B (fallback manual):** se em algum aparelho o navegador não devolver o
app sozinho, a tela de login tem um campo para **colar o endereço** que ficou
na barra do navegador (`http://127.0.0.1:...?code=...`) e concluir o login na
mão (`completar_login_manual` em `vetvoice/infrastructure/google/auth.py`).

**Multi-cliente:** cada usuário loga na própria conta; a planilha
`VetVoice - <Fazenda>` nasce no Drive do próprio usuário. Enquanto o app OAuth
estiver em modo *Testing* no Google Cloud Console, só e-mails adicionados como
**test users** conseguem logar — para liberar geral é preciso publicar o app
OAuth (verificação do Google).

---

## 🖐️ Rolagem e toque (decisão consolidada — não reinventar)

`RolagemComCampos` (`vetvoice/presentation/widgets.py`) é um `ScrollView`
**puro** do Kivy, sem nenhum override de toque. O Kivy já arbitra sozinho
"arraste = rolar / toque parado = clique ou foco no campo"; as tentativas de
fazer isso à mão eram justamente o que quebrava a rolagem. Só dois valores
documentados são calibrados:

```python
scroll_timeout = 400      # ms segurando o toque antes de entregá-lo ao botão
scroll_distance = dp(20)  # dedo andou isso dentro do tempo? então é rolagem
```

Se a rolagem der problema de novo, ajuste **só esses dois números** — não
sobrescreva `on_touch_down`/`on_touch_up`.

---

## 🏗️ Arquitetura (Clean Architecture)

Dependências apontam para dentro: interface → casos de uso → domínio. A
infraestrutura implementa as *portas* do domínio. Regra de negócio não vive em
tela.

```
main.py                              # ponto de entrada (Buildozer/PyInstaller)
vetvoice/
├── shared/config.py                 # caminhos, opções de chips, interruptores
├── domain/
│   ├── entities.py                  # Atendimento
│   ├── ports.py                     # interfaces (repos, autenticador, transcritor…)
│   └── parsing/                     # parser híbrido + segmentação da Ronda
├── application/                     # casos de uso (analise, atendimentos,
│   │                                # sincronizacao, autenticacao, dicionarios…)
│   └── servicos.py                  # agregado injetado em todas as telas
├── infrastructure/
│   ├── persistence/sqlite.py        # banco local + tabela de dicionários
│   ├── speech/transcritor.py        # SpeechRecognizer do Android (contínuo)
│   └── google/auth.py, sheets.py    # OAuth PKCE + envio ao Sheets
├── presentation/                    # Kivy: theme, widgets, dialogs, screens/
└── composition.py                   # monta e injeta as dependências reais
tests/                               # parser, fluxo, segmentação da ronda
```

### Gravação contínua (sem desligar sozinha)

`infrastructure/speech/transcritor.py`: o `SpeechRecognizer` do Android encerra
a sessão em qualquer pausa. O app intercepta os erros de silêncio (códigos 6 e
7), **reinicia o reconhecedor automaticamente** e vai acumulando as frases; só
finaliza quando o usuário toca para parar.

---

## ⚙️ Como o APK é gerado (GitHub Actions)

Workflow único: `.github/workflows/build-otimizado.yml`. Roda a cada push na
`main` ou manualmente (aba **Actions** → *Run workflow*). O APK sai como
artefato **`vacavet-apk`** na página da execução.

Pontos críticos do workflow (não remover):

1. **Java 17 forçado** (`JAVA_HOME_17_X64`) — o Android Gradle Plugin exige
   Java 17; sem isso o build quebra com *"requires Java 17"*.
2. **Segredo `GOOGLE_OAUTH_CLIENT_JSON`** — o JSON do cliente OAuth **nunca**
   vai para o git (o repositório é público!). Ele é gravado em
   `credenciais/oauth_client.json` na hora do build, a partir do *secret* do
   repositório. Sem o segredo o app compila e só desativa o login Google.
3. **Ubuntu 22.04** — tem o `libtinfo5` que o toolchain do Android precisa.
4. **Caches ccache/Buildozer** — aceleram recompilações. Para forçar um build
   100% do zero, mude o sufixo de versão das chaves de cache (`-v2`, `-v3`...).

### Rodar no computador (para testar a interface)

```bash
pip install -r requirements.txt
python main.py
```

---

## ❓ Problemas conhecidos e onde mexer

| Sintoma | Causa/solução |
|---------|---------------|
| Tela preta ao voltar do login | Falta de `on_pause` → já corrigido em `presentation/app.py`. Não remover. |
| Login autoriza mas não volta ao app | Usar o campo "cole o endereço do navegador" na tela de login. |
| `Error 403: access_denied` no Google | E-mail não está como *test user* no Google Cloud Console (app em modo Testing). |
| Rolagem não funciona sobre botões | Calibrar `scroll_timeout`/`scroll_distance` em `RolagemComCampos` — nunca sobrescrever métodos de toque. |
| Gravação para sozinha | Ver `_ERROS_SILENCIO`/`_reiniciar()` no `transcritor.py`. |
| Build falha com erro de Java | Conferir o `export JAVA_HOME="$JAVA_HOME_17_X64"` no workflow. |
| Ronda não separa os animais | Falar o marcador antes do número: `"vaca 12"`, `"brinco 40"`, `"animal 7"`. |
