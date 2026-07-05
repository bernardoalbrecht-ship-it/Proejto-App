"""
infrastructure/nlp_openai.py
----------------------------
Parser OPCIONAL baseado no GPT da OpenAI (pago), como implementação alternativa
da porta `ParserFala`. É infraestrutura porque depende de um serviço externo.

Só é usado se USAR_IA_OPENAI = True (config) e houver chave. Em qualquer falha,
o `composition` mantém o parser híbrido offline como fallback.
"""

import json

from vetvoice.domain.ports import ParserFala
from vetvoice.domain.parsing import ParserHibridoOffline
from vetvoice.shared import config

_CAMPOS = (
    "propriedade", "id_vaca", "procedimento", "raca", "peso_kg", "idade_anos",
    "status_reprodutivo", "diagnostico", "medicacoes", "proxima_acao",
    "observacoes",
)


class ParserOpenAI(ParserFala):
    """Usa o GPT para interpretar a fala; cai no parser offline em caso de erro.
    A correção de transcrição continua usando o offline (rápido, sem custo)."""

    def __init__(self, fallback: ParserFala = None):
        self._fallback = fallback or ParserHibridoOffline()

    def analisar(self, transcricao: str) -> dict:
        try:
            return self._analisar_com_ia(transcricao)
        except Exception as erro:  # noqa: BLE001
            print(f"[AVISO] IA falhou ({erro}). Usando o parser offline.")
            return self._fallback.analisar(transcricao)

    def corrigir_transcricao(self, texto: str) -> str:
        return self._fallback.corrigir_transcricao(texto)

    def _analisar_com_ia(self, transcricao: str) -> dict:
        from openai import OpenAI

        cliente = OpenAI(api_key=config.OPENAI_API_KEY)
        instrucao = (
            "Você é assistente de um veterinário de gado leiteiro no Brasil. "
            "A partir da frase falada, extraia um JSON com as chaves exatamente: "
            "propriedade, id_vaca, procedimento, raca, peso_kg, idade_anos, "
            "status_reprodutivo, diagnostico, medicacoes, proxima_acao, "
            "observacoes. 'propriedade' é o nome da fazenda/cabanha citada. "
            "Responda SOMENTE o JSON, sem texto extra."
        )
        resposta = cliente.chat.completions.create(
            model=config.OPENAI_MODELO,
            messages=[
                {"role": "system", "content": instrucao},
                {"role": "user", "content": transcricao},
            ],
            temperature=0,
        )
        conteudo = resposta.choices[0].message.content.strip()
        conteudo = conteudo.replace("```json", "").replace("```", "").strip()
        dados = json.loads(conteudo)
        for chave in _CAMPOS:
            dados.setdefault(chave, "")
        return dados
