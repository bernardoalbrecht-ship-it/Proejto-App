"""
domain/parsing
--------------
Parser híbrido do VetVoice — regra de negócio pura (sem framework, sem I/O).
Transforma a fala transcrita em campos estruturados, 100% offline.

Camadas internas: text -> fuzzy -> vocabulary -> lexicon -> extractors -> pipeline.

`ParserHibridoOffline` adapta as funções do pipeline à porta `ParserFala`, para
ser injetado nos casos de uso.
"""

from vetvoice.domain.parsing import pipeline
from vetvoice.domain.ports import ParserFala


class ParserHibridoOffline(ParserFala):
    """Implementação offline da porta `ParserFala` (dicionários + regex +
    contexto + inferência). É a implementação padrão do app."""

    def analisar(self, transcricao: str) -> dict:
        return pipeline.analisar(transcricao or "")

    def corrigir_transcricao(self, texto: str) -> str:
        return pipeline.corrigir_transcricao(texto or "")


__all__ = ["ParserHibridoOffline"]
