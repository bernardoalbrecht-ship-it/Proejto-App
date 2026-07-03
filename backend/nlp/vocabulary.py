"""
nlp/vocabulary.py
-----------------
Modelo de DOMÍNIO do parser: um `Term` (entidade canônica com sinônimos e
metadados) e um `Vocabulary` (coleção pesquisável de termos).

É aqui que mora a "inteligência de dicionário": cada termo aceita vários
sinônimos, e a busca compara contra o texto normalizado usando correspondência
exata e aproximada (fuzzy). Adicionar um medicamento novo é só acrescentar um
`Term` no lexicon — nenhuma outra parte do código muda.
"""

from dataclasses import dataclass, field

from backend.nlp import fuzzy
from backend.nlp.text import normalizar


@dataclass(frozen=True)
class Term:
    """Uma entidade do vocabulário (um medicamento, um diagnóstico...).

    - canonico: nome "bonito" exibido/salvo (com acentos), ex. "Metronidazol".
    - sinonimos: formas como pode ser dito/transcrito, ex. ("metro", "metron").
                 O próprio canônico é sempre incluído como sinônimo.
    - meta: dados auxiliares livres (dose_comum, idade_aproximada, etc.).
    """
    canonico: str
    sinonimos: tuple = ()
    meta: dict = field(default_factory=dict)

    def chaves_normalizadas(self) -> list:
        """Todas as formas de busca (canônico + sinônimos), normalizadas e sem
        duplicatas, ordenadas da mais longa para a mais curta — assim o match
        prefere a expressão mais específica ('gir leiteiro' antes de 'gir')."""
        formas = {normalizar(self.canonico)}
        formas.update(normalizar(s) for s in self.sinonimos)
        formas.discard("")
        return sorted(formas, key=len, reverse=True)


class Vocabulary:
    """Coleção ordenada de `Term`. A ORDEM importa: em caso de empate, vence o
    termo declarado primeiro (dá para priorizar termos mais comuns/específicos).
    """

    def __init__(self, termos):
        self._termos = list(termos)

    def __iter__(self):
        return iter(self._termos)

    def encontrar(self, texto_norm: str, tokens: list = None) -> Term:
        """Primeiro termo cujo alguma chave aparece no texto. None se nenhum."""
        for termo in self._termos:
            for chave in termo.chaves_normalizadas():
                if fuzzy.contem(texto_norm, chave, tokens):
                    return termo
        return None

    def encontrar_todos(self, texto_norm: str, tokens: list = None) -> list:
        """Todos os termos citados, na ordem do vocabulário (sem repetição)."""
        achados = []
        for termo in self._termos:
            for chave in termo.chaves_normalizadas():
                if fuzzy.contem(texto_norm, chave, tokens):
                    achados.append(termo)
                    break
        return achados

    def casar_palavra(self, palavra_norm: str) -> Term:
        """Termo cujo alguma chave de UMA palavra bate (exata/fuzzy) com a
        palavra dada. Usado para canonizar um token isolado (ex.: uma droga
        capturada ao lado de uma dose)."""
        for termo in self._termos:
            for chave in termo.chaves_normalizadas():
                if " " in chave:
                    continue
                if fuzzy.quase_igual(palavra_norm, chave):
                    return termo
        return None

    def sinonimos_de_palavra_unica(self) -> set:
        """Conjunto de todas as chaves de UMA palavra do vocabulário. Serve de
        'dicionário conhecido' para corrigir a transcrição exibida."""
        vocab = set()
        for termo in self._termos:
            for chave in termo.chaves_normalizadas():
                if " " not in chave:
                    vocab.add(chave)
        return vocab
