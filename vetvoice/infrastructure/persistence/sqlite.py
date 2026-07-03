"""
persistence/sqlite.py
---------------------
Implementação SQLite das portas de repositório. É o banco LOCAL onde os
atendimentos ficam guardados no aparelho, mesmo sem internet (offline-first).

SQLite já vem com o Python, não precisa de servidor, funciona 100% offline —
ideal para um app de campo.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional

from vetvoice.domain.entities import Atendimento
from vetvoice.domain.ports import RepositorioAtendimentos, RepositorioPropriedades
from vetvoice.shared import config


def conectar(caminho=None):
    """Abre conexão. row_factory permite ler colunas pelo nome."""
    conexao = sqlite3.connect(caminho or config.DATABASE_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco(caminho=None):
    """Cria as tabelas se ainda não existirem (idempotente)."""
    with conectar(caminho) as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS atendimentos (
                id_banco             INTEGER PRIMARY KEY AUTOINCREMENT,
                id_vaca              TEXT NOT NULL,
                data                 TEXT,
                hora                 TEXT,
                veterinario          TEXT,
                propriedade          TEXT,
                tipo_producao        TEXT,
                procedimento         TEXT,
                raca                 TEXT,
                peso_kg              TEXT,
                idade_anos           TEXT,
                status_reprodutivo   TEXT,
                diagnostico          TEXT,
                medicacoes           TEXT,
                proxima_acao         TEXT,
                observacoes          TEXT,
                transcricao_original TEXT,
                sincronizado         INTEGER DEFAULT 0,
                criado_em            TEXT,
                atualizado_em        TEXT
            )
            """
        )
        # Migração leve: bancos de versões anteriores podem não ter a coluna.
        try:
            conexao.execute("ALTER TABLE atendimentos ADD COLUMN tipo_producao TEXT")
        except sqlite3.OperationalError:
            pass  # coluna já existe
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS propriedades (
                nome      TEXT PRIMARY KEY,
                criado_em TEXT
            )
            """
        )
        conexao.commit()


def _linha_para_atendimento(linha: sqlite3.Row) -> Atendimento:
    return Atendimento(
        id_banco=linha["id_banco"],
        id_vaca=linha["id_vaca"],
        data=linha["data"],
        hora=linha["hora"],
        veterinario=linha["veterinario"],
        propriedade=linha["propriedade"],
        tipo_producao=(linha["tipo_producao"] if "tipo_producao" in linha.keys()
                       else "") or "",
        procedimento=linha["procedimento"],
        raca=linha["raca"],
        peso_kg=linha["peso_kg"],
        idade_anos=linha["idade_anos"],
        status_reprodutivo=linha["status_reprodutivo"],
        diagnostico=linha["diagnostico"],
        medicacoes=linha["medicacoes"],
        proxima_acao=linha["proxima_acao"],
        observacoes=linha["observacoes"],
        transcricao_original=linha["transcricao_original"],
        sincronizado=linha["sincronizado"],
    )


class RepositorioAtendimentosSQLite(RepositorioAtendimentos):
    """Guarda os atendimentos no SQLite local."""

    def __init__(self, caminho=None):
        self._caminho = caminho

    def salvar(self, atendimento: Atendimento) -> int:
        agora = datetime.now().isoformat()
        with conectar(self._caminho) as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO atendimentos (
                    id_vaca, data, hora, veterinario, propriedade, tipo_producao,
                    procedimento, raca, peso_kg, idade_anos, status_reprodutivo,
                    diagnostico, medicacoes, proxima_acao, observacoes,
                    transcricao_original, sincronizado, criado_em, atualizado_em
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    atendimento.id_vaca, atendimento.data, atendimento.hora,
                    atendimento.veterinario, atendimento.propriedade,
                    atendimento.tipo_producao, atendimento.procedimento,
                    atendimento.raca, atendimento.peso_kg, atendimento.idade_anos,
                    atendimento.status_reprodutivo, atendimento.diagnostico,
                    atendimento.medicacoes, atendimento.proxima_acao,
                    atendimento.observacoes, atendimento.transcricao_original,
                    atendimento.sincronizado, agora, agora,
                ),
            )
            conexao.commit()
            atendimento.id_banco = cursor.lastrowid
            return cursor.lastrowid

    def listar(self, limite: int = 100,
               id_vaca: Optional[str] = None) -> List[Atendimento]:
        with conectar(self._caminho) as conexao:
            if id_vaca:
                linhas = conexao.execute(
                    "SELECT * FROM atendimentos WHERE id_vaca=? "
                    "ORDER BY criado_em DESC LIMIT ?", (id_vaca, limite),
                ).fetchall()
            else:
                linhas = conexao.execute(
                    "SELECT * FROM atendimentos ORDER BY criado_em DESC LIMIT ?",
                    (limite,),
                ).fetchall()
        return [_linha_para_atendimento(l) for l in linhas]

    def listar_pendentes(self) -> List[Atendimento]:
        with conectar(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT * FROM atendimentos WHERE sincronizado=0 ORDER BY criado_em"
            ).fetchall()
        return [_linha_para_atendimento(l) for l in linhas]

    def marcar_sincronizado(self, id_banco: int) -> None:
        with conectar(self._caminho) as conexao:
            conexao.execute(
                "UPDATE atendimentos SET sincronizado=1 WHERE id_banco=?",
                (id_banco,))
            conexao.commit()

    def excluir(self, id_banco: int) -> None:
        if id_banco is None:
            raise ValueError("Não é possível excluir sem id_banco.")
        with conectar(self._caminho) as conexao:
            conexao.execute("DELETE FROM atendimentos WHERE id_banco=?", (id_banco,))
            conexao.commit()

    def excluir_da_vaca(self, id_vaca: str) -> int:
        with conectar(self._caminho) as conexao:
            cursor = conexao.execute(
                "DELETE FROM atendimentos WHERE id_vaca=?", (id_vaca,))
            conexao.commit()
            return cursor.rowcount

    def excluir_da_propriedade(self, propriedade: str) -> int:
        with conectar(self._caminho) as conexao:
            cursor = conexao.execute(
                "DELETE FROM atendimentos WHERE propriedade=?", (propriedade,))
            conexao.execute("DELETE FROM propriedades WHERE nome=?", (propriedade,))
            conexao.commit()
            return cursor.rowcount


class RepositorioPropriedadesSQLite(RepositorioPropriedades):
    """Cadastro de fazendas: une as cadastradas explicitamente com as que
    aparecem nos atendimentos."""

    def __init__(self, caminho=None):
        self._caminho = caminho

    def adicionar(self, nome: str) -> None:
        nome = (nome or "").strip()
        if not nome:
            return
        with conectar(self._caminho) as conexao:
            conexao.execute(
                "INSERT OR IGNORE INTO propriedades (nome, criado_em) VALUES (?, ?)",
                (nome, datetime.now().isoformat()))
            conexao.commit()

    def listar(self) -> List[str]:
        with conectar(self._caminho) as conexao:
            linhas = conexao.execute(
                """
                SELECT nome, MAX(ultima) AS ultima FROM (
                    SELECT propriedade AS nome, MAX(criado_em) AS ultima
                    FROM atendimentos
                    WHERE propriedade IS NOT NULL AND TRIM(propriedade) != ''
                    GROUP BY propriedade
                    UNION ALL
                    SELECT nome, criado_em AS ultima FROM propriedades
                )
                GROUP BY nome
                ORDER BY ultima DESC
                """
            ).fetchall()
        return [l["nome"] for l in linhas]
