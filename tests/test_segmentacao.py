"""
test_segmentacao.py
-------------------
Testes da segmentação de RONDA (dividir a fala de vários animais por número).

Rode com:  python3 tests/test_segmentacao.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vetvoice.domain.parsing.segmentacao import segmentar_por_animal


def test_vazio_nao_quebra():
    assert segmentar_por_animal("") == []
    assert segmentar_por_animal("bom dia sem número nenhum") == []


def test_dois_animais():
    r = segmentar_por_animal("vaca 12 inseminação prenha vaca 15 mastite")
    assert [id_ for id_, _ in r] == ["12", "15"]
    assert "inseminação" in r[0][1]
    assert "mastite" in r[1][1]


def test_une_mesmo_animal_seguido():
    r = segmentar_por_animal("vaca 8 prenha vaca 8 aplicar 5ml de corticoide")
    assert len(r) == 1
    assert r[0][0] == "8"
    assert "corticoide" in r[0][1]


def test_reconhece_brinco_e_animal():
    r = segmentar_por_animal("brinco 100 vazia animal 200 vacinação")
    assert [id_ for id_, _ in r] == ["100", "200"]


def test_ignora_texto_antes_do_primeiro_animal():
    r = segmentar_por_animal("fazenda boa vista vaca 3 palpação")
    assert len(r) == 1
    assert r[0][0] == "3"
    assert r[0][1].startswith("vaca 3")


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
