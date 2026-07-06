"""
test_parser.py
--------------
Testes do parser híbrido (vetvoice.domain.parsing), incluindo os exemplos do PRD
e o comportamento que a versão anterior já suportava (contra regressão).

Rode com:  python -m pytest tests/test_parser.py   (ou python -m tests.test_parser)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vetvoice.domain.parsing import ParserHibridoOffline
from vetvoice.shared import config

_parser = ParserHibridoOffline()


def analisar(t):
    return _parser.analisar(t)


# --- Exemplos do PRD -------------------------------------------------------

def test_prd_jose_fez_iatf():
    r = analisar("José fez IATF")
    assert r["procedimento"] == "Inseminação Artificial"
    assert r["propriedade"] == ""


def test_prd_metronidazol_3ml():
    assert analisar("Metronidazol 3 ml")["medicacoes"] == "Metronidazol 3ml"


def test_prd_dose_por_extenso():
    r = analisar("José, novilha, metronidazol três ml")
    assert "Metronidazol 3ml" in r["medicacoes"]
    assert r["idade_anos"] == "Novilha"


def test_prd_novilha():
    assert analisar("Novilha")["idade_anos"] == "Novilha"


def test_prd_primipara():
    assert analisar("Primípara")["idade_anos"] == "Primípara"


def test_prd_frase_completa():
    r = analisar("José, novilha, mastite, metronidazol três ml")
    assert r["idade_anos"] == "Novilha"
    assert r["diagnostico"] == "Mastite"
    assert "Metronidazol 3ml" in r["medicacoes"]


def test_prd_diagnostico_desconhecido_vira_outro():
    r = analisar("suspeita de inflamação pós-parto")
    assert r["diagnostico"] != ""
    assert r["diagnostico"] not in config.DIAGNOSTICO_OPCOES


# --- Proteção contra regressão (comportamento antigo) ----------------------

def test_fluxo_inseminacao_vazia():
    r = analisar("Vaca 123, feita inseminação artificial com sêmen, animal vazia")
    assert r["id_vaca"] == "123"
    assert r["procedimento"] == "Inseminação Artificial"
    assert r["status_reprodutivo"] == "Vazia"


def test_negacao_prenha_vira_vazia():
    assert analisar("vaca 5 não deu prenhe")["status_reprodutivo"] == "Vazia"


def test_prenha_direto():
    assert analisar("vaca 7 gestante confirmada")["status_reprodutivo"] == "Prenha"


def test_dose_antes_da_droga():
    assert analisar("5 ml de corticoide")["medicacoes"] == "Corticoide 5ml"


def test_medicamento_sem_dose():
    assert analisar("apliquei antibiótico")["medicacoes"] == "Antibiótico"


def test_propriedade_com_gatilho():
    r = analisar("fazenda Boa Vista, vaca 10")
    assert r["propriedade"] == "Boa Vista"
    assert r["id_vaca"] == "10"


def test_id_nao_pega_numero_da_dose():
    assert analisar("metronidazol 3 ml")["id_vaca"] == ""


def test_peso_e_idade():
    r = analisar("vaca 8 pesa 450 kg, 3 anos, holandês")
    assert r["peso_kg"] == "450"
    assert r["idade_anos"] == "3"
    assert r["raca"] == "Holandês"


def test_fuzzy_erro_de_voz():
    assert "Flunixin Meglumine" in analisar("apliquei flunixim")["medicacoes"]


def test_corrigir_transcricao():
    assert "vazia" in _parser.corrigir_transcricao("a vaca esta vasia").lower()


def test_brangus_nao_vira_angus():
    # "angus" é substring de "brangus"; o match não pode confundir.
    assert analisar("vaca 10 brangus")["raca"] == "Brangus"


def test_racas_ampliadas():
    assert analisar("vaca 3 hereford")["raca"] == "Hereford"
    assert analisar("vaca 4 holstein")["raca"] == "Holandês"


def test_status_nao_vira_medicacao():
    # "ceftiofur 5ml prenha": 'prenha' não pode ser capturada como remédio.
    r = analisar("vaca 15 ceftiofur 5ml prenha")
    assert r["medicacoes"] == "Ceftiofur 5ml"
    assert r["status_reprodutivo"] == "Prenha"


def test_diagnostico_ampliado_pneumonia():
    assert analisar("vaca 9 pneumonia")["diagnostico"] == "Pneumonia"


def test_todas_as_chaves_presentes():
    r = analisar("qualquer coisa")
    for chave in ("propriedade", "id_vaca", "procedimento", "raca", "peso_kg",
                  "idade_anos", "status_reprodutivo", "diagnostico",
                  "medicacoes", "proxima_acao", "observacoes"):
        assert chave in r


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
