"""
models.py
---------
Define a estrutura de um "Atendimento" — ou seja, o registro de uma consulta a uma vaca.
Usamos uma dataclass, que é uma forma simples do Python guardar dados organizados.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Atendimento:
    """Representa um único atendimento a uma vaca."""

    id_vaca: str = ""                     # número do brinco, ex: "123"
    data: str = ""                        # ex: "01/07/2026"
    hora: str = ""                        # ex: "14:35"
    veterinario: str = ""
    propriedade: str = ""
    tipo_producao: str = ""               # "Corte" ou "Leite"
    procedimento: str = ""                # ex: "Inseminação Artificial"
    raca: str = ""                        # ex: "Holandesa"
    peso_kg: str = ""                     # ex: "580"
    idade_anos: str = ""                  # ex: "4"
    status_reprodutivo: str = ""          # ex: "Vazia", "Gestante", "Lactante"
    diagnostico: str = ""
    medicacoes: str = ""
    proxima_acao: str = ""
    observacoes: str = ""
    transcricao_original: str = ""        # o texto exato que foi falado
    sincronizado: int = 0                 # 0 = ainda não enviado, 1 = já na nuvem
    id_banco: int = field(default=None)   # id interno do banco (preenchido depois)

    def preencher_data_hora(self):
        """Preenche data e hora automaticamente com o momento atual."""
        agora = datetime.now()
        self.data = agora.strftime("%d/%m/%Y")
        self.hora = agora.strftime("%H:%M")

    def como_dicionario(self):
        """Converte o atendimento em dicionário (útil para salvar/enviar)."""
        d = asdict(self)
        d.pop("id_banco", None)  # o id do banco não vai para a planilha
        return d
