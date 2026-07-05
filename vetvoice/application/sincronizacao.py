"""
application/sincronizacao.py
----------------------------
Caso de uso da sincronização (offline-first). Orquestra as portas de
repositório e de nuvem:

  1) pega os atendimentos pendentes do banco;
  2) se a nuvem não estiver disponível (sem login), marca como sincronizado
     localmente (modo simulado — o app continua utilizável);
  3) se estiver, envia e só então marca como sincronizado — nunca perde
     registros.
"""

from vetvoice.domain.ports import RepositorioAtendimentos, ServicoNuvem


class SincronizarAtendimentos:
    def __init__(self, repo: RepositorioAtendimentos, nuvem: ServicoNuvem):
        self._repo = repo
        self._nuvem = nuvem

    def executar(self, propriedade: str) -> dict:
        pendentes = self._repo.listar_pendentes()

        if not self._nuvem.esta_disponivel():
            for a in pendentes:
                self._repo.marcar_sincronizado(a.id_banco)
            return {"enviados": len(pendentes), "erros": 0, "modo": "simulado"}

        resultado = self._nuvem.enviar(propriedade, pendentes)
        if resultado.get("ok"):
            for a in pendentes:
                self._repo.marcar_sincronizado(a.id_banco)
            return {"enviados": len(pendentes), "erros": 0, "modo": "real",
                    "link": resultado.get("link")}

        return {"enviados": 0, "erros": len(pendentes) or 1, "modo": "real",
                "detalhe": resultado.get("detalhe", "Tente novamente.")}
