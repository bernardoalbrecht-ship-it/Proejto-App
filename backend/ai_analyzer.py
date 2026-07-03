"""
ai_analyzer.py  (fachada de compatibilidade)
--------------------------------------------
Ponto de entrada histórico da análise da fala. Todo o motor foi refatorado para
o pacote `backend.nlp` (parser híbrido: normalização + dicionários + regex +
contexto + inferência). Este arquivo apenas ORQUESTRA os dois modos e mantém as
funções públicas antigas (`analisar`, `corrigir_transcricao`) para que a
interface, os testes e o seed continuem funcionando sem alteração.

Modos:
  1) OFFLINE (padrão): parser híbrido em `backend.nlp`. Grátis, sem internet.
  2) IA (opcional): GPT da OpenAI, ligado por USAR_IA_OPENAI no config.py.

Em ambos os casos o resultado é uma SUGESTÃO — o veterinário revisa antes de
salvar.
"""

from backend import config
from backend.nlp import analisar as _analisar_offline
from backend.nlp import corrigir_transcricao  # re-exportado (mantém a API)

__all__ = ["analisar", "corrigir_transcricao"]

# Chaves garantidas no resultado (contrato com a interface).
_CAMPOS = (
    "propriedade", "id_vaca", "procedimento", "raca", "peso_kg", "idade_anos",
    "status_reprodutivo", "diagnostico", "medicacoes", "proxima_acao",
    "observacoes",
)


def analisar(transcricao: str) -> dict:
    """Recebe o texto falado e devolve os campos sugeridos do atendimento.
    Usa a IA (paga) se estiver habilitada; senão, o parser híbrido offline."""
    if config.USAR_IA_OPENAI and config.OPENAI_API_KEY:
        try:
            return _analisar_com_ia(transcricao)
        except Exception as erro:  # noqa: BLE001 — cai para o offline em qualquer falha
            print(f"[AVISO] IA falhou ({erro}). Usando o parser offline.")
    return _analisar_offline(transcricao)


# ---------------------------------------------------------------------------
# MODO IA — OpenAI GPT (opcional/pago)
# ---------------------------------------------------------------------------
def _analisar_com_ia(transcricao: str) -> dict:
    from openai import OpenAI

    cliente = OpenAI(api_key=config.OPENAI_API_KEY)
    instrucao = (
        "Você é assistente de um veterinário de gado leiteiro no Brasil. "
        "A partir da frase falada, extraia um JSON com as chaves exatamente: "
        "propriedade, id_vaca, procedimento, raca, peso_kg, idade_anos, "
        "status_reprodutivo, diagnostico, medicacoes, proxima_acao, observacoes. "
        "'propriedade' é o nome da fazenda/cabanha citada. Responda SOMENTE o "
        "JSON, sem texto extra."
    )
    resposta = cliente.chat.completions.create(
        model=config.OPENAI_MODELO,
        messages=[
            {"role": "system", "content": instrucao},
            {"role": "user", "content": transcricao},
        ],
        temperature=0,
    )

    import json

    conteudo = resposta.choices[0].message.content.strip()
    conteudo = conteudo.replace("```json", "").replace("```", "").strip()
    dados = json.loads(conteudo)
    for chave in _CAMPOS:
        dados.setdefault(chave, "")
    return dados
