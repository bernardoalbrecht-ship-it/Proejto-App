# 🐄 Sistema de Atendimento Veterinário por Voz

Aplicativo para registrar atendimentos em vacas leiteiras **falando no microfone**.
O veterinário diz, por exemplo: *"Vaca 123, feita inseminação artificial, animal vazia"*,
e o app transcreve, organiza em campos e guarda os dados — funcionando **offline** e
sincronizando com a **nuvem (Google Sheets)** quando houver internet.

Roda no **Windows (.exe)** e no **Android (APK)** com o mesmo código.

---

## ✅ O que já funciona sem pagar nada

Por padrão o app vem em **MODO DE TESTE**, que é gratuito:
- Transcrição pelo reconhecimento **gratuito** do Google Web (só precisa de internet).
- Preenchimento automático dos campos por **regras em português** (sem IA paga).
- Dados salvos localmente no aparelho (banco SQLite).
- Se o microfone não pegar, você pode **digitar a frase** e o app preenche os campos.

Quando quiser, é só ativar os recursos da nuvem no arquivo `vetvoice/shared/config.py`.

---

## 📁 Estrutura do projeto (Clean Architecture)

As dependências apontam sempre para dentro: a interface usa os casos de uso, que
usam o domínio; a infraestrutura implementa as *portas* do domínio. Nenhuma regra
de negócio vive na interface.

```
vetvoice/
├── shared/config.py               # LIGA/DESLIGA recursos, caminhos, colunas
├── domain/                        # regras de negócio (sem framework)
│   ├── entities.py                # Atendimento
│   ├── ports.py                   # interfaces (repositórios e serviços)
│   └── parsing/                   # parser híbrido (dicionários + regex + contexto)
├── application/                   # casos de uso (orquestração)
│   ├── analise.py  atendimentos.py  propriedades.py
│   ├── sincronizacao.py  autenticacao.py  sessao.py  servicos.py
├── infrastructure/                # implementações concretas
│   ├── persistence/sqlite.py      # banco local (SQLite) + seed.py
│   ├── speech/transcritor.py      # transforma fala em texto (Vosk/Android)
│   ├── google/auth.py  google/sheets.py   # login + envio à nuvem
│   └── nlp_openai.py              # parser opcional com GPT
├── presentation/                  # telas Kivy (Windows/Android)
│   ├── theme.py  widgets.py  dialogs.py  gravacao.py
│   └── screens/  app.py
└── composition.py                 # monta e injeta as dependências reais
main.py                            # ponto de entrada (.exe e APK) -> presentation.app
tests/                             # test_parser.py, test_fluxo.py
```

---

## 🚀 Como testar no computador (passo a passo)

### 1. Instalar o Python
Baixe em [python.org](https://www.python.org/downloads/) (versão 3.11 ou mais nova).
Na instalação, marque a opção **"Add Python to PATH"**.

### 2. Instalar as bibliotecas
Abra o terminal (Prompt de Comando) na pasta do projeto e rode:
```bash
pip install -r requirements.txt
```
> Se der erro no **PyAudio** no Windows, rode: `pip install pipwin` e depois `pipwin install pyaudio`.

### 3. (Opcional) Colocar dados de exemplo
Para já ver atendimentos no histórico:
```bash
python -m vetvoice.infrastructure.persistence.seed
```

### 4. Abrir o app
```bash
python main.py
```
Pronto! A janela do aplicativo vai abrir.

---

## 🖥️ Como gerar o .EXE (Windows)

> ⚠️ O `.exe` só pode ser gerado **no próprio Windows** (não dá para fazer no Linux/Mac).

1. Instale o PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Gere o executável:
   ```bash
   pyinstaller --name AtendimentoVet --onefile --windowed main.py
   ```
3. O arquivo `.exe` aparecerá na pasta `dist/`.

> Dica: Kivy às vezes precisa de ajustes no `.spec` gerado. Se o `.exe` não abrir,
> peça ao Claude Code para ajustar o arquivo `AtendimentoVet.spec` incluindo os
> `hooks` do Kivy.

---

## 📱 Como gerar o APK (Android)

> ⚠️ O APK é gerado no **Linux** (ou WSL no Windows) usando o **Buildozer**.

1. Instale o Buildozer:
   ```bash
   pip install buildozer
   ```
2. Na pasta do projeto, rode:
   ```bash
   buildozer -v android debug
   ```
3. O APK aparecerá na pasta `bin/`. Passe para o celular e instale.

O arquivo `buildozer.spec` já vem configurado com as permissões de **microfone** e
**internet** necessárias.

---

## ☁️ Como ativar a nuvem (opcional, quando estiver pronto)

Abra `vetvoice/shared/config.py` e mude de `False` para `True` o que quiser usar:

| Opção | O que ativa | Precisa de |
|-------|-------------|-----------|
| `USAR_GOOGLE_CLOUD_SPEECH` | Transcrição paga (mais precisa) | Conta Google Cloud + JSON |
| `USAR_IA_OPENAI` | Análise inteligente com GPT | Chave da OpenAI |
| `USAR_GOOGLE_SHEETS` | Envio para planilha na nuvem | JSON de conta de serviço Google |

Coloque os arquivos de credencial (`.json`) na pasta `credenciais/`.

---

## 💡 Exemplos de frases que o app entende (modo gratuito)

- "Vaca 123, feita inseminação artificial com sêmen, animal vazia"
- "Vaca 321, feito diagnóstico de gestação, implantado chip hormonal, gestante"
- "Vaca 104, diagnosticada cetose subclínica, tratamento com propileno glicol"
- "Vaca 101, exame ginecológico sem anormalidades, aplicada vacina, lactante"

O app identifica automaticamente: número da vaca, procedimento, status reprodutivo,
medicações e sugere a próxima ação.

---

## ❓ Problemas comuns

- **Microfone não funciona:** digite a frase no campo de transcrição e toque em
  "Preencher campos". Funciona igual.
- **Sem internet:** tudo continua salvo no aparelho; sincronize depois.
- **Erro ao instalar Kivy/PyAudio:** confira a versão do Python (use 3.11+).
