"""
test_dicionarios.py
-------------------
Testes das LISTAS EDITÁVEIS: persistência dos termos criados pelo usuário e a
junção "opções de fábrica + termos do usuário" (sem duplicar, de fábrica antes).

Rode com:  python3 tests/test_dicionarios.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vetvoice.application.dicionarios import GestaoDicionarios
from vetvoice.infrastructure.persistence import sqlite


def _gestao_temporaria():
    caminho = os.path.join(tempfile.mkdtemp(), "teste.db")
    sqlite.inicializar_banco(caminho)
    return GestaoDicionarios(sqlite.RepositorioDicionariosSQLite(caminho))


def test_lista_vazia_devolve_so_a_base():
    g = _gestao_temporaria()
    assert g.opcoes("raca", ["Nelore", "Angus"]) == ["Nelore", "Angus"]


def test_termo_do_usuario_entra_no_fim():
    g = _gestao_temporaria()
    g.adicionar("raca", "Wagyu")
    assert g.opcoes("raca", ["Nelore", "Angus"]) == ["Nelore", "Angus", "Wagyu"]


def test_nao_duplica_termo_ja_de_fabrica():
    g = _gestao_temporaria()
    g.adicionar("raca", "Nelore")  # já é de fábrica
    assert g.opcoes("raca", ["Nelore", "Angus"]) == ["Nelore", "Angus"]


def test_categorias_sao_independentes():
    g = _gestao_temporaria()
    g.adicionar("raca", "Wagyu")
    g.adicionar("procedimento", "Biópsia")
    assert g.personalizados("raca") == ["Wagyu"]
    assert g.personalizados("procedimento") == ["Biópsia"]


def test_excluir_remove_o_termo():
    g = _gestao_temporaria()
    g.adicionar("diagnostico", "Fotossensibilização")
    g.excluir("diagnostico", "Fotossensibilização")
    assert g.personalizados("diagnostico") == []


def test_adicionar_ignora_vazio():
    g = _gestao_temporaria()
    g.adicionar("raca", "   ")
    assert g.personalizados("raca") == []


if __name__ == "__main__":
    import traceback

    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for f in funcs:
        try:
            f()
            print(f"[OK] {f.__name__}")
        except Exception:
            falhas += 1
            print(f"[FALHOU] {f.__name__}")
            traceback.print_exc()
    print(f"\n{len(funcs) - falhas}/{len(funcs)} testes passaram.")
    sys.exit(1 if falhas else 0)
