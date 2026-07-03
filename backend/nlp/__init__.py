"""
backend.nlp
-----------
Motor de NLP (parser híbrido) do VetVoice. Transforma a fala transcrita em
campos estruturados de um atendimento, 100% offline.

Camadas (baixo acoplamento, alta coesão):
    text        -> normalização/tokenização
    fuzzy       -> correspondência aproximada (erros de voz)
    vocabulary  -> modelo Term/Vocabulary
    lexicon     -> os dicionários do domínio (dado puro, expansível)
    extractors  -> regex e associação medicamento<->dose
    pipeline    -> orquestração por prioridade

Fachada pública: use `analisar()` e `corrigir_transcricao()`.
"""

from backend.nlp.pipeline import analisar, corrigir_transcricao

__all__ = ["analisar", "corrigir_transcricao"]
