"""
nlp/fuzzy.py
------------
Correspondência APROXIMADA de palavras — tolera os erros típicos do
reconhecimento de voz (letra trocada, faltando ou sobrando), sem depender de
biblioteca externa (roda leve em celular).

Regra de ouro: quanto mais curta a palavra, menos erro se tolera — senão
"vaca" viraria "vacina" por acaso. Palavras muito curtas exigem escrita exata.
"""

# Abaixo deste tamanho, uma chave só é aceita por escrita EXATA (alto risco de
# "quase bater" em outra coisa por acaso).
TAMANHO_MINIMO_PARA_FUZZY = 5


def distancia_edicao(a: str, b: str) -> int:
    """Distância de Levenshtein: nº mínimo de letras a inserir/remover/trocar
    para transformar 'a' em 'b'. Implementação iterativa O(len(a)*len(b))."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    linha_anterior = list(range(len(b) + 1))
    for i, letra_a in enumerate(a, start=1):
        linha_atual = [i]
        for j, letra_b in enumerate(b, start=1):
            custo = 0 if letra_a == letra_b else 1
            linha_atual.append(min(
                linha_anterior[j] + 1,          # remoção
                linha_atual[j - 1] + 1,         # inserção
                linha_anterior[j - 1] + custo,  # substituição
            ))
        linha_anterior = linha_atual
    return linha_anterior[-1]


def erros_tolerados(tamanho_chave: int) -> int:
    """Orçamento de erros conforme o tamanho da chave. Ex.: 'flunixim' ->
    'flunixin' é aceito (1 erro); 'vaca' -> 'vacina' não (chave curta)."""
    return 1 if tamanho_chave <= 8 else 2


def quase_igual(palavra: str, chave: str) -> bool:
    """True se 'palavra' é igual ou suficientemente próxima de 'chave'. Ambas
    já devem vir normalizadas (minúsculas, sem acento)."""
    if palavra == chave:
        return True
    if len(chave) < TAMANHO_MINIMO_PARA_FUZZY:
        return False
    tolerancia = erros_tolerados(len(chave))
    if abs(len(palavra) - len(chave)) > tolerancia:
        return False
    return distancia_edicao(palavra, chave) <= tolerancia


def contem(texto_norm: str, chave_norm: str, tokens: list = None) -> bool:
    """A 'chave' (1+ palavras) aparece em 'texto'? Tenta match EXATO de
    substring (rápido) e, se falhar, match APROXIMADO por janela de tokens.
    Todos os argumentos já devem vir normalizados."""
    if not chave_norm:
        return False
    if chave_norm in texto_norm:
        return True
    if len(chave_norm) < TAMANHO_MINIMO_PARA_FUZZY:
        return False

    if tokens is None:
        tokens = texto_norm.split()
    partes = chave_norm.split()
    n = len(partes)
    if n == 0 or len(tokens) < n:
        return False

    tolerancia = erros_tolerados(len(chave_norm))
    for i in range(len(tokens) - n + 1):
        janela = " ".join(tokens[i:i + n])
        if abs(len(janela) - len(chave_norm)) > tolerancia:
            continue
        if distancia_edicao(janela, chave_norm) <= tolerancia:
            return True
    return False
