"""
database.py
-----------
Cuida do banco de dados LOCAL (SQLite). É aqui que os atendimentos ficam guardados
no aparelho, mesmo sem internet. Depois, quando houver conexão, eles são enviados
para a nuvem (Google Sheets) e marcados como "sincronizados".

Por que SQLite? Porque já vem junto com o Python, não precisa instalar servidor,
funciona 100% offline e é perfeito para um app de campo.
"""

import sqlite3
from datetime import datetime

from backend.config import DATABASE_PATH
from backend.models import Atendimento


def conectar():
    """Abre uma conexão com o banco. row_factory deixa ler colunas pelo nome."""
    conexao = sqlite3.connect(DATABASE_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    """Cria a tabela de atendimentos se ela ainda não existir."""
    with conectar() as conexao:
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
        # Migração leve: se o banco já existia de uma versão anterior (sem a
        # coluna tipo_producao), adiciona-a sem apagar os dados existentes.
        try:
            conexao.execute("ALTER TABLE atendimentos ADD COLUMN tipo_producao TEXT")
        except sqlite3.OperationalError:
            pass  # coluna já existe
        # Tabela própria de propriedades/fazendas: permite CADASTRAR uma fazenda
        # antes de ter qualquer atendimento nela (o botão "Adicionar propriedade").
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS propriedades (
                nome      TEXT PRIMARY KEY,
                criado_em TEXT
            )
            """
        )
        conexao.commit()


def salvar_atendimento(atendimento: Atendimento) -> int:
    """Salva um novo atendimento e devolve o id gerado pelo banco."""
    agora = datetime.now().isoformat()
    with conectar() as conexao:
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
                atendimento.tipo_producao,
                atendimento.procedimento, atendimento.raca, atendimento.peso_kg,
                atendimento.idade_anos, atendimento.status_reprodutivo,
                atendimento.diagnostico, atendimento.medicacoes,
                atendimento.proxima_acao, atendimento.observacoes,
                atendimento.transcricao_original, atendimento.sincronizado,
                agora, agora,
            ),
        )
        conexao.commit()
        return cursor.lastrowid


def atualizar_atendimento(atendimento: Atendimento):
    """Atualiza um atendimento existente (precisa ter id_banco)."""
    if atendimento.id_banco is None:
        raise ValueError("Não é possível atualizar sem id_banco.")
    agora = datetime.now().isoformat()
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE atendimentos SET
                id_vaca=?, data=?, hora=?, veterinario=?, propriedade=?,
                tipo_producao=?, procedimento=?, raca=?, peso_kg=?, idade_anos=?,
                status_reprodutivo=?, diagnostico=?, medicacoes=?,
                proxima_acao=?, observacoes=?, transcricao_original=?,
                sincronizado=?, atualizado_em=?
            WHERE id_banco=?
            """,
            (
                atendimento.id_vaca, atendimento.data, atendimento.hora,
                atendimento.veterinario, atendimento.propriedade,
                atendimento.tipo_producao,
                atendimento.procedimento, atendimento.raca, atendimento.peso_kg,
                atendimento.idade_anos, atendimento.status_reprodutivo,
                atendimento.diagnostico, atendimento.medicacoes,
                atendimento.proxima_acao, atendimento.observacoes,
                atendimento.transcricao_original, atendimento.sincronizado,
                agora, atendimento.id_banco,
            ),
        )
        conexao.commit()


def listar_atendimentos(limite: int = 100, id_vaca: str = None) -> list:
    """Lista os atendimentos mais recentes. Pode filtrar por id da vaca."""
    with conectar() as conexao:
        if id_vaca:
            linhas = conexao.execute(
                "SELECT * FROM atendimentos WHERE id_vaca=? "
                "ORDER BY criado_em DESC LIMIT ?",
                (id_vaca, limite),
            ).fetchall()
        else:
            linhas = conexao.execute(
                "SELECT * FROM atendimentos ORDER BY criado_em DESC LIMIT ?",
                (limite,),
            ).fetchall()
    return [_linha_para_atendimento(l) for l in linhas]


def adicionar_propriedade(nome: str):
    """Cadastra uma fazenda explicitamente (sem precisar de atendimento).
    Se já existir, não faz nada."""
    nome = (nome or "").strip()
    if not nome:
        return
    with conectar() as conexao:
        conexao.execute(
            "INSERT OR IGNORE INTO propriedades (nome, criado_em) VALUES (?, ?)",
            (nome, datetime.now().isoformat()),
        )
        conexao.commit()


def listar_propriedades() -> list:
    """Devolve os nomes de propriedade conhecidos (mais recentes primeiro), para
    o veterinário escolher em vez de digitar de novo. Une DUAS fontes: as
    cadastradas explicitamente (tabela propriedades) e as que aparecem nos
    atendimentos — assim uma fazenda recém-adicionada, ainda sem atendimento,
    também aparece na lista."""
    with conectar() as conexao:
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


def excluir_atendimento(id_banco: int):
    """Apaga um único atendimento pelo id do banco."""
    if id_banco is None:
        raise ValueError("Não é possível excluir sem id_banco.")
    with conectar() as conexao:
        conexao.execute("DELETE FROM atendimentos WHERE id_banco=?", (id_banco,))
        conexao.commit()


def excluir_atendimentos_da_vaca(id_vaca: str) -> int:
    """Apaga todos os atendimentos de uma vaca. Devolve quantos foram apagados."""
    with conectar() as conexao:
        cursor = conexao.execute(
            "DELETE FROM atendimentos WHERE id_vaca=?", (id_vaca,)
        )
        conexao.commit()
        return cursor.rowcount


def excluir_propriedade(propriedade: str) -> int:
    """Apaga TODOS os atendimentos de uma propriedade/fazenda.
    Devolve quantos registros foram apagados. Como as propriedades não têm
    tabela própria (são derivadas dos atendimentos), apagar todos os
    atendimentos dela faz a fazenda sumir da lista de propriedades salvas."""
    with conectar() as conexao:
        cursor = conexao.execute(
            "DELETE FROM atendimentos WHERE propriedade=?", (propriedade,)
        )
        # Remove também do cadastro explícito, se estiver lá.
        conexao.execute("DELETE FROM propriedades WHERE nome=?", (propriedade,))
        conexao.commit()
        return cursor.rowcount


def listar_nao_sincronizados() -> list:
    """Retorna só os atendimentos que ainda não foram enviados para a nuvem."""
    with conectar() as conexao:
        linhas = conexao.execute(
            "SELECT * FROM atendimentos WHERE sincronizado=0 ORDER BY criado_em"
        ).fetchall()
    return [_linha_para_atendimento(l) for l in linhas]


def marcar_como_sincronizado(id_banco: int):
    """Marca um atendimento como já enviado para a nuvem."""
    with conectar() as conexao:
        conexao.execute(
            "UPDATE atendimentos SET sincronizado=1 WHERE id_banco=?", (id_banco,)
        )
        conexao.commit()


def _linha_para_atendimento(linha: sqlite3.Row) -> Atendimento:
    """Converte uma linha do banco em um objeto Atendimento."""
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
