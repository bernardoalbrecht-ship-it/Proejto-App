"""
test_fluxo.py
-------------
Testa o fluxo de ponta a ponta pela camada de aplicação (casos de uso), sem
microfone nem nuvem real: fala (texto) -> análise -> salvar (SQLite temporário)
-> sincronizar (nuvem fake). Verifica também o modo "simulado" offline.

Rode:  python -m pytest tests/test_fluxo.py   (ou python -m tests.test_fluxo)
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vetvoice.application.atendimentos import GestaoAtendimentos
from vetvoice.application.analise import AnalisarFala
from vetvoice.application.sincronizacao import SincronizarAtendimentos
from vetvoice.domain.parsing import ParserHibridoOffline
from vetvoice.domain.ports import ServicoNuvem
from vetvoice.infrastructure.persistence import sqlite


def _repo_temporario():
    """Cria um repositório SQLite num arquivo temporário isolado por teste."""
    caminho = os.path.join(tempfile.mkdtemp(), "teste.db")
    sqlite.inicializar_banco(caminho)
    return sqlite.RepositorioAtendimentosSQLite(caminho)


class _NuvemFake(ServicoNuvem):
    """Nuvem simulada: registra o que foi enviado, sem rede."""
    def __init__(self, disponivel=True, ok=True):
        self._disponivel = disponivel
        self._ok = ok
        self.enviados = []

    def esta_disponivel(self) -> bool:
        return self._disponivel

    def enviar(self, propriedade, atendimentos) -> dict:
        self.enviados.append((propriedade, list(atendimentos)))
        if self._ok:
            return {"ok": True, "link": "http://exemplo/plan"}
        return {"ok": False, "detalhe": "falha simulada"}


def test_analise_preenche_campos():
    campos = AnalisarFala(ParserHibridoOffline()).analisar(
        "Vaca 123, feita inseminação artificial com sêmen, animal vazia")
    assert campos["id_vaca"] == "123"
    assert campos["procedimento"] == "Inseminação Artificial"
    assert campos["status_reprodutivo"] == "Vazia"


def test_registrar_e_sincronizar_na_nuvem():
    repo = _repo_temporario()
    gestao = GestaoAtendimentos(repo)
    parser = ParserHibridoOffline()

    fala = "Vaca 123, feita inseminação artificial com sêmen, animal vazia"
    campos = parser.analisar(fala)
    atendimento = gestao.registrar(
        id_vaca=campos["id_vaca"], propriedade="Fazenda X",
        tipo_producao="Leite", transcricao_original=fala, campos=campos)
    assert atendimento.id_banco is not None
    assert gestao.contar_pendentes() == 1

    nuvem = _NuvemFake(disponivel=True, ok=True)
    resultado = SincronizarAtendimentos(repo, nuvem).executar("Fazenda X")
    assert resultado["modo"] == "real"
    assert resultado["enviados"] == 1
    assert resultado["erros"] == 0
    assert gestao.contar_pendentes() == 0
    assert nuvem.enviados[0][0] == "Fazenda X"


def test_sincronizacao_simulada_sem_login():
    repo = _repo_temporario()
    gestao = GestaoAtendimentos(repo)
    gestao.registrar(id_vaca="9", propriedade="F", tipo_producao="Leite",
                     transcricao_original="", campos={})
    resultado = SincronizarAtendimentos(
        repo, _NuvemFake(disponivel=False)).executar("F")
    assert resultado["modo"] == "simulado"
    assert resultado["enviados"] == 1
    assert gestao.contar_pendentes() == 0


def test_falha_na_nuvem_nao_marca_sincronizado():
    repo = _repo_temporario()
    gestao = GestaoAtendimentos(repo)
    gestao.registrar(id_vaca="1", propriedade="F", tipo_producao="Leite",
                     transcricao_original="", campos={})
    resultado = SincronizarAtendimentos(
        repo, _NuvemFake(disponivel=True, ok=False)).executar("F")
    assert resultado["erros"] >= 1
    assert gestao.contar_pendentes() == 1  # nada perdido, segue pendente


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
