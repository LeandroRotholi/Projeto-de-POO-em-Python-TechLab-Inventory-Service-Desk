"""Repositório (DAO) de chamados de suporte em SQLite."""

from __future__ import annotations

import sqlite3

from techlab.dominio.ativo_ti import AtivoTI
from techlab.dominio.chamado_suporte import ChamadoSuporte
from techlab.excecoes import (
    ChamadoNaoEncontradoException,
    DadosInvalidosException,
    EquipamentoNaoEncontradoException,
    FalhaPersistenciaException,
)
from techlab.interfaces import IConexaoBD, IPersistencia


class ChamadoRepository(IPersistencia[ChamadoSuporte]):
    def __init__(
        self, conexao: IConexaoBD, repositorio_ativos: IPersistencia[AtivoTI]
    ) -> None:
        self._conexao = conexao
        self._ativos = repositorio_ativos

    @property
    def _db(self) -> sqlite3.Connection:
        return self._conexao.obter_conexao()

    def _para_chamado(
        self, linha: sqlite3.Row, cache: dict[int, AtivoTI] | None = None
    ) -> ChamadoSuporte:
        ativo_id = linha["ativo_id"]
        if cache is not None and ativo_id in cache:
            ativo = cache[ativo_id]
        else:
            ativo = self._ativos.buscar_por_id(ativo_id)
            if cache is not None:
                cache[ativo_id] = ativo
        return ChamadoSuporte(
            id=linha["id"],
            titulo=linha["titulo"],
            descricao=linha["descricao"],
            prioridade=linha["prioridade"],
            ativo_relacionado=ativo,
            data_abertura=linha["data_abertura"],
            status=linha["status"],
        )

    def salvar(self, chamado: ChamadoSuporte) -> ChamadoSuporte:
        ativo_id = chamado.ativo_relacionado.id
        if ativo_id is None:
            raise DadosInvalidosException(
                "O equipamento do chamado precisa estar cadastrado (sem id)."
            )
        sql = (
            "INSERT INTO chamados (titulo, descricao, prioridade, data_abertura, "
            "status, ativo_id) VALUES (?, ?, ?, ?, ?, ?)"
        )
        parametros = (
            chamado.titulo,
            chamado.descricao,
            int(chamado.prioridade),
            chamado.data_abertura.isoformat(),
            chamado.status.value,
            ativo_id,
        )
        try:
            with self._db:
                cursor = self._db.execute(sql, parametros)
        except sqlite3.IntegrityError as erro:
            raise EquipamentoNaoEncontradoException(ativo_id) from erro
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao salvar chamado: {erro}") from erro
        chamado.id = cursor.lastrowid
        return chamado

    def buscar_por_id(self, id: int) -> ChamadoSuporte:
        try:
            linha = self._db.execute(
                "SELECT * FROM chamados WHERE id = ?", (id,)
            ).fetchone()
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao buscar chamado: {erro}") from erro
        if linha is None:
            raise ChamadoNaoEncontradoException(id)
        return self._para_chamado(linha)

    def listar(self) -> list[ChamadoSuporte]:
        try:
            linhas = self._db.execute("SELECT * FROM chamados ORDER BY id").fetchall()
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao listar chamados: {erro}") from erro
        cache: dict[int, AtivoTI] = {}
        return [self._para_chamado(linha, cache) for linha in linhas]

    def listar_por_ativo(self, ativo_id: int) -> list[ChamadoSuporte]:
        try:
            linhas = self._db.execute(
                "SELECT * FROM chamados WHERE ativo_id = ? ORDER BY id", (ativo_id,)
            ).fetchall()
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao listar chamados: {erro}") from erro
        cache: dict[int, AtivoTI] = {}
        return [self._para_chamado(linha, cache) for linha in linhas]

    def atualizar(self, chamado: ChamadoSuporte) -> ChamadoSuporte:
        if chamado.id is None:
            raise DadosInvalidosException("Não é possível atualizar um chamado sem id.")
        sql = (
            "UPDATE chamados SET titulo = ?, descricao = ?, prioridade = ?, "
            "status = ? WHERE id = ?"
        )
        parametros = (
            chamado.titulo,
            chamado.descricao,
            int(chamado.prioridade),
            chamado.status.value,
            chamado.id,
        )
        try:
            with self._db:
                cursor = self._db.execute(sql, parametros)
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao atualizar chamado: {erro}") from erro
        if cursor.rowcount == 0:
            raise ChamadoNaoEncontradoException(chamado.id)
        return chamado

    def remover(self, id: int) -> None:
        try:
            with self._db:
                cursor = self._db.execute("DELETE FROM chamados WHERE id = ?", (id,))
        except sqlite3.Error as erro:
            raise FalhaPersistenciaException(f"Erro ao remover chamado: {erro}") from erro
        if cursor.rowcount == 0:
            raise ChamadoNaoEncontradoException(id)
