"""
seed_data.py
------------
Coloca DADOS FICTÍCIOS no banco para você testar o app sem precisar sair a campo.
Rode este arquivo uma vez (python -m backend.seed_data) e abra o app: já verá
alguns atendimentos de exemplo no histórico.
"""

from backend import database
from backend.models import Atendimento
from backend.ai_analyzer import analisar


EXEMPLOS = [
    {
        "transcricao": "Vaca 101, feito exame ginecológico sem anormalidades, "
                       "aplicada vacina contra mastite, animal lactante",
        "raca": "Holandesa", "peso": "580", "idade": "4",
    },
    {
        "transcricao": "Vaca 102, feita inseminação artificial com sêmen, "
                       "animal vazia, sem intercorrências",
        "raca": "Jersey", "peso": "450", "idade": "2",
    },
    {
        "transcricao": "Vaca 103, feito diagnóstico de gestação por ultrassom, "
                       "gestante, implantado chip hormonal",
        "raca": "Girolando", "peso": "520", "idade": "3",
    },
    {
        "transcricao": "Vaca 104, diagnosticada cetose subclínica, iniciado "
                       "tratamento com propileno glicol",
        "raca": "Holandesa", "peso": "560", "idade": "5",
    },
]


def popular():
    database.inicializar_banco()
    for exemplo in EXEMPLOS:
        campos = analisar(exemplo["transcricao"])
        atendimento = Atendimento(
            id_vaca=campos["id_vaca"],
            veterinario="Dr. Exemplo",
            propriedade="Fazenda Teste",
            procedimento=campos["procedimento"],
            raca=exemplo["raca"],
            peso_kg=exemplo["peso"],
            idade_anos=exemplo["idade"],
            status_reprodutivo=campos["status_reprodutivo"],
            diagnostico=campos["diagnostico"],
            medicacoes=campos["medicacoes"],
            proxima_acao=campos["proxima_acao"],
            observacoes=campos["observacoes"],
            transcricao_original=exemplo["transcricao"],
        )
        atendimento.preencher_data_hora()
        database.salvar_atendimento(atendimento)
    print(f"{len(EXEMPLOS)} atendimentos de exemplo inseridos com sucesso.")


if __name__ == "__main__":
    popular()
