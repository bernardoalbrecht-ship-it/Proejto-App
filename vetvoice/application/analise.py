"""
application/analise.py
----------------------
Caso de uso de análise da fala: aplica o parser (porta `ParserFala`) para
preencher os campos do atendimento e para corrigir a transcrição exibida.
"""

from vetvoice.domain.ports import ParserFala


class AnalisarFala:
    def __init__(self, parser: ParserFala):
        self._parser = parser

    def analisar(self, texto: str) -> dict:
        """Interpreta a fala e devolve os campos sugeridos do atendimento."""
        return self._parser.analisar(texto or "")

    def corrigir(self, texto: str) -> str:
        """Corrige erros prováveis de transcrição no texto exibido."""
        return self._parser.corrigir_transcricao(texto or "")
