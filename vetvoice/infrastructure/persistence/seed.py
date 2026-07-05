"""
persistence/seed.py
-------------------
Popula o banco com atendimentos fictícios para testar o app sem sair a campo.
Rode:  python -m vetvoice.infrastructure.persistence.seed
"""

from vetvoice.domain.parsing import ParserHibridoOffline
from vetvoice.infrastructure.persistence import sqlite
from vetvoice.infrastructure.persistence.sqlite import (
    RepositorioAtendimentosSQLite,
)
from vetvoice.application.atendimentos import GestaoAtendimentos

EXEMPLOS = [
    "Fazenda Teste, vaca 101, exame ginecológico sem anormalidades, "
    "aplicada vacina contra mastite, animal lactante, holandês, 4 anos",
    "Fazenda Teste, vaca 102, inseminação artificial com sêmen, animal vazia, "
    "jersey, 2 anos",
    "Fazenda Teste, vaca 103, diagnóstico de gestação por ultrassom, gestante, "
    "implantado chip hormonal, girolando, 3 anos",
    "Fazenda Teste, vaca 104, cetose subclínica, propileno glicol, 5 anos",
]


def popular():
    sqlite.inicializar_banco()
    parser = ParserHibridoOffline()
    gestao = GestaoAtendimentos(RepositorioAtendimentosSQLite())
    for frase in EXEMPLOS:
        campos = parser.analisar(frase)
        gestao.registrar(
            id_vaca=campos["id_vaca"] or "0",
            propriedade="Fazenda Teste",
            tipo_producao="Leite",
            transcricao_original=frase,
            campos=campos)
    print(f"{len(EXEMPLOS)} atendimentos de exemplo inseridos com sucesso.")


if __name__ == "__main__":
    popular()
