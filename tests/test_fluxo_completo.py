"""
test_fluxo_completo.py
----------------------
Teste que simula o uso real do app SEM precisar de microfone ou nuvem:
fala (texto) -> análise -> salvar no banco -> sincronizar.

Rode com:  python -m tests.test_fluxo_completo
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import database, ai_analyzer, google_sheets_sync
from backend.models import Atendimento


def test_fluxo():
    database.inicializar_banco()

    # 1) Simula a fala do veterinário (o que viria do microfone)
    fala = "Vaca 123, feita inseminação artificial com sêmen, animal vazia"

    # 2) Análise organiza em campos
    campos = ai_analyzer.analisar(fala)
    assert campos["id_vaca"] == "123", "Deveria extrair o número da vaca"
    assert campos["procedimento"] == "Inseminação Artificial"
    assert campos["status_reprodutivo"] == "Vazia"
    print("✅ Análise da fala correta")

    # 3) Cria e salva o atendimento
    atendimento = Atendimento(
        id_vaca=campos["id_vaca"],
        veterinario="Dr. Teste",
        propriedade="Fazenda Automatizada",
        procedimento=campos["procedimento"],
        status_reprodutivo=campos["status_reprodutivo"],
        diagnostico=campos["diagnostico"],
        medicacoes=campos["medicacoes"],
        proxima_acao=campos["proxima_acao"],
        transcricao_original=fala,
    )
    atendimento.preencher_data_hora()
    id_banco = database.salvar_atendimento(atendimento)
    assert id_banco is not None
    print(f"✅ Atendimento salvo no banco (id {id_banco})")

    # 4) Confere que está pendente de sincronização
    pendentes_antes = len(database.listar_nao_sincronizados())
    assert pendentes_antes >= 1
    print(f"✅ {pendentes_antes} registro(s) aguardando sincronização")

    # 5) Sincroniza (modo simulado no teste)
    resultado = google_sheets_sync.sincronizar("Fazenda Automatizada")
    assert resultado["enviados"] >= 1
    print(f"✅ Sincronização concluída: {resultado}")

    # 6) Agora não deve haver mais pendentes
    assert len(database.listar_nao_sincronizados()) == 0
    print("✅ Todos os registros sincronizados")

    print("\n🎉 FLUXO COMPLETO FUNCIONANDO DE PONTA A PONTA!")


if __name__ == "__main__":
    test_fluxo()
