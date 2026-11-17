"""Repositório (DAO) de ativos de TI em SQLite.

Proteção contra SQL Injection: TODOS os valores vindos do usuário entram
na consulta por parâmetros (``?``). Nomes de colunas dinâmicos (ORDER BY)
só são aceitos se estiverem em uma lista de permissão fixa.
"""

from __future__ import annotations

import json
import sqlite3

from techlab.dominio.ativo_ti import AtivoTI
from techlab.dominio.fabrica import ativo_de_dict
from techlab.excecoes import (
    DadosInvalidosException,
    EquipamentoNaoEncontradoException,
    FalhaPersistenciaException,
    OperacaoNaoPermitidaException,
    PatrimonioDuplicadoException,
)
from techlab.interfaces import IConexaoBD, IPersistencia

COLUNAS_ORDENAVEIS = frozenset(
    {"id", "tipo", "codigo_patrimonio", "modelo", "data_aquisicao", "status"}
)


def _escapar_like(termo: str) -> str:
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AtivoRepository(IPersistencia[AtivoTI]):
    def __init__(self, conexao: IConexaoBD) -> None:
        self._conexao = conexao

    @property
    def _db(self) -> sqlite3.Connection:
        return self._conexao.obter_conexao()

    @staticmethod
    def _para_ativo(linha: sqlite3.Row) -> AtivoTI:
        return ativo_de_dict(
            {
                "id": linha["id"],
                "tipo": linha["tipo"],
                "codigo_patrimonio": linha["codigo_patrimonio"],
                "modelo": linha["modelo"],
                "data_aquisicao": linha["data_aquisicao"],
                "status": linha["status"],
                "detalhes": json.loads(linha["detalhes"]),
            }
        )

    # ------------------------------ CREATE ------------------------------
    def salvar(self, ativo: AtivoTI) -> AtivoTI:
        sql = (
            "INSERT INTO ativos (tipo, codigo_patrimonio, modelo, data_aquisicao, "
            "status, detalhes) VALUES (?, ?, ?, ?, ?, ?)"
        )
        dados = ativo.para_dict()
        parametros = (
            dados["tipo"],
            dados["codigo_patrimonio"],
            dados["modelo"],
            dados["data_aquisicao"],
            dados["status"],
            json.dumps(dados["detalhes"], ensure_ascii=False),
        )
        try:
            with self._db:  # commit automático; rollback em caso de erro
                cursor = self._db.execute(sql, parametros)
        except sqlite3.IntegrityError as erro:
            if "UNIQUE" in str(erro).upper():
                raise PatrimonioDuplicadoException(ativo.codigo_patrimonio) from erro
            raise DadosInvalidosException(f"Dados rejeitados pelo banco: {erro}") from erro
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao salvar ativo: {erro}") from erro
        ativo.id = cursor.lastrowid
        return ativo

    # ------------------------------- READ -------------------------------
    def buscar_por_id(self, id: int) -> AtivoTI:
        try:
            linha = self._db.execute(
                "SELECT * FROM ativos WHERE id = ?", (id,)
            ).fetchone()
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao buscar ativo: {erro}") from erro
        if linha is None:
            raise EquipamentoNaoEncontradoException(id)
        return self._para_ativo(linha)

    def listar(
        self, ordenar_por: str = "id", decrescente: bool = False
    ) -> list[AtivoTI]:
        if ordenar_por not in COLUNAS_ORDENAVEIS:
            raise DadosInvalidosException(f"Coluna de ordenação inválida: {ordenar_por!r}")
        direcao = "DESC" if decrescente else "ASC"
        # ordenar_por e direcao foram validados contra valores fixos acima.
        sql = f"SELECT * FROM ativos ORDER BY {ordenar_por} {direcao}"
        try:
            linhas = self._db.execute(sql).fetchall()
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao listar ativos: {erro}") from erro
        return [self._para_ativo(linha) for linha in linhas]

    def buscar_por_modelo(self, termo: str) -> list[AtivoTI]:
        """Busca parcial no modelo usando LIKE parametrizado."""
        sql = "SELECT * FROM ativos WHERE modelo LIKE ? ESCAPE '\\' ORDER BY modelo"
        try:
            linhas = self._db.execute(sql, (f"%{_escapar_like(termo)}%",)).fetchall()
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro na busca: {erro}") from erro
        return [self._para_ativo(linha) for linha in linhas]

    # ------------------------------ UPDATE ------------------------------
    def atualizar(self, ativo: AtivoTI) -> AtivoTI:
        if ativo.id is None:
            raise DadosInvalidosException("Não é possível atualizar um ativo sem id.")
        sql = (
            "UPDATE ativos SET tipo = ?, codigo_patrimonio = ?, modelo = ?, "
            "data_aquisicao = ?, status = ?, detalhes = ? WHERE id = ?"
        )
        dados = ativo.para_dict()
        parametros = (
            dados["tipo"],
            dados["codigo_patrimonio"],
            dados["modelo"],
            dados["data_aquisicao"],
            dados["status"],
            json.dumps(dados["detalhes"], ensure_ascii=False),
            ativo.id,
        )
        try:
            with self._db:
                cursor = self._db.execute(sql, parametros)
        except sqlite3.IntegrityError as erro:
            if "UNIQUE" in str(erro).upper():
                raise PatrimonioDuplicadoException(ativo.codigo_patrimonio) from erro
            raise DadosInvalidosException(f"Dados rejeitados pelo banco: {erro}") from erro
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao atualizar ativo: {erro}") from erro
        if cursor.rowcount == 0:
            raise EquipamentoNaoEncontradoException(ativo.id)
        return ativo

    # ------------------------------ DELETE ------------------------------
    def remover(self, id: int) -> None:
        try:
            with self._db:
                cursor = self._db.execute("DELETE FROM ativos WHERE id = ?", (id,))
        except sqlite3.IntegrityError as erro:
            raise OperacaoNaoPermitidaException(
                "Não é possível remover um equipamento que possui chamados vinculados."
            ) from erro
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao remover ativo: {erro}") from erro
        if cursor.rowcount == 0:
            raise EquipamentoNaoEncontradoException(id)
