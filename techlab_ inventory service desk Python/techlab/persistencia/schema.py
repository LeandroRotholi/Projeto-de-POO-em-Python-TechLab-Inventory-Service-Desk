"""Criação das tabelas do banco relacional."""

from __future__ import annotations

import sqlite3

from techlab.excecoes import FalhaPersistenciaException
from techlab.interfaces import IConexaoBD

SCRIPT_SCHEMA = """
CREATE TABLE IF NOT EXISTS ativos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo              TEXT NOT NULL
                      CHECK (tipo IN ('SERVIDOR', 'ESTACAO_TRABALHO', 'DISPOSITIVO_REDE')),
    codigo_patrimonio TEXT NOT NULL UNIQUE,
    modelo            TEXT NOT NULL,
    data_aquisicao    TEXT NOT NULL,
    status            TEXT NOT NULL
                      CHECK (status IN ('ATIVO', 'EM_MANUTENCAO', 'INATIVO', 'DESCARTADO')),
    detalhes          TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS chamados (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo        TEXT NOT NULL,
    descricao     TEXT NOT NULL,
    prioridade    INTEGER NOT NULL CHECK (prioridade BETWEEN 1 AND 4),
    data_abertura TEXT NOT NULL,
    status        TEXT NOT NULL
                  CHECK (status IN ('ABERTO', 'EM_ATENDIMENTO', 'FECHADO')),
    ativo_id      INTEGER NOT NULL,
    FOREIGN KEY (ativo_id) REFERENCES ativos (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_chamados_ativo ON chamados (ativo_id);
"""


def criar_schema(conexao: IConexaoBD) -> None:
    try:
        db = conexao.obter_conexao()
        with db:
            db.executescript(SCRIPT_SCHEMA)
    except sqlite3.Error as erro:
        raise FalhaPersistenciaException(f"Erro ao criar o schema: {erro}") from erro
