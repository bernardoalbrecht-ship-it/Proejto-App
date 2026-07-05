"""
domain/entities.py
------------------
Entidades do domínio veterinário. Uma entidade é um objeto de negócio com
identidade e regras próprias — independente de banco, tela ou framework.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Atendimento:
    """Um único atendimento a uma vaca."""

    id_vaca: str = ""                     # número do brinco, ex: "123"
    data: str = ""                        # ex: "01/07/2026"
    hora: str = ""                        # ex: "14:35"
    veterinario: str = ""
    propriedade: str = ""
    tipo_producao: str = ""               # "Corte" ou "Leite"
    procedimento: str = ""
    raca: str = ""
    peso_kg: str = ""
    idade_anos: str = ""                  # aceita categoria (Novilha...) como texto
    status_reprodutivo: str = ""          # "Prenha" / "Vazia"
    diagnostico: str = ""
    medicacoes: str = ""
    proxima_acao: str = ""
    observacoes: str = ""
    transcricao_original: str = ""        # o texto exato que foi falado
    sincronizado: int = 0                 # 0 = pendente, 1 = já na nuvem
    id_banco: int = field(default=None)   # id interno do banco (preenchido depois)

    def preencher_data_hora(self):
        """Preenche data e hora com o momento atual."""
        agora = datetime.now()
        self.data = agora.strftime("%d/%m/%Y")
        self.hora = agora.strftime("%H:%M")

    def como_dicionario(self):
        """Converte em dicionário (sem o id interno do banco)."""
        d = asdict(self)
        d.pop("id_banco", None)
        return d
