"""
application/atendimentos.py
---------------------------
Casos de uso dos atendimentos: registrar, listar (histórico) e excluir. A
interface nunca fala com o banco diretamente — passa por aqui.
"""

from typing import List, Optional

from vetvoice.domain.entities import Atendimento
from vetvoice.domain.ports import RepositorioAtendimentos

# Campos preenchíveis a partir da fala/ficha (o resto vem da sessão/relógio).
CAMPOS_FICHA = (
    "procedimento", "raca", "peso_kg", "idade_anos", "status_reprodutivo",
    "diagnostico", "medicacoes", "proxima_acao", "observacoes",
)


class GestaoAtendimentos:
    def __init__(self, repo: RepositorioAtendimentos):
        self._repo = repo

    def registrar(self, id_vaca: str, propriedade: str, tipo_producao: str,
                  transcricao_original: str, campos: dict) -> Atendimento:
        """Monta o atendimento a partir dos dados da ficha, carimba data/hora e
        salva localmente. Devolve a entidade já com o id do banco."""
        atendimento = Atendimento(
            id_vaca=id_vaca.strip(),
            propriedade=propriedade,
            tipo_producao=tipo_producao,
            transcricao_original=transcricao_original.strip(),
        )
        for chave in CAMPOS_FICHA:
            setattr(atendimento, chave, (campos.get(chave) or "").strip())
        atendimento.preencher_data_hora()
        self._repo.salvar(atendimento)
        return atendimento

    def listar(self, limite: int = 100,
               id_vaca: Optional[str] = None) -> List[Atendimento]:
        return self._repo.listar(limite=limite, id_vaca=id_vaca)

    def contar_pendentes(self) -> int:
        return len(self._repo.listar_pendentes())

    def excluir(self, id_banco: int) -> None:
        self._repo.excluir(id_banco)

    def excluir_vaca(self, id_vaca: str) -> int:
        return self._repo.excluir_da_vaca(id_vaca)
