"""Conexão com SQLite (implementação de IConexaoBD)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from techlab.excecoes import FalhaConexaoBDException
from techlab.interfaces import IConexaoBD


class ConexaoSQLite(IConexaoBD):
    def __init__(self, caminho: str | Path = ":memory:") -> None:
        self._caminho = str(caminho)
        self._conn: sqlite3.Connection | None = None

    def conectar(self) -> None:
        if self._conn is not None:
            return
        try:
            if self._caminho != ":memory:":
                Path(self._caminho).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._caminho)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        except (sqlite3.Error, OSError) as erro:
            raise FalhaConexaoBDException(
                f"Não foi possível abrir o banco '{self._caminho}': {erro}"
            ) from erro
        self._conn = conn

    def desconectar(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def obter_conexao(self) -> sqlite3.Connection:
        if self._conn is None:
            raise FalhaConexaoBDException(
                "A conexão com o banco não está aberta. Chame conectar() antes."
            )
        return self._conn

    @property
    def conectado(self) -> bool:
        return self._conn is not None

    def __enter__(self) -> "ConexaoSQLite":
        self.conectar()
        return self

    def __exit__(self, *_args) -> None:
        self.desconectar()
