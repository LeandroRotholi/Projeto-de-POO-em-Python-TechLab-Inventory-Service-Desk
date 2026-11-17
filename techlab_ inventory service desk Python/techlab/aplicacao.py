"""Composição da aplicação (injeção de dependências manual).

É o único lugar que conhece as implementações concretas. Todo o resto do
sistema conversa apenas com interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from techlab.excecoes import DadosInvalidosException
from techlab.interfaces import IConexaoBD, INotificavel
from techlab.notificacao import NotificadorConsole
from techlab.persistencia import (
    AtivoCsvRepository,
    AtivoRepository,
    ChamadoCsvRepository,
    ChamadoRepository,
    ConexaoSQLite,
    criar_schema,
)
from techlab.servicos import InventarioService, ServiceDesk

BACKENDS = ("sqlite", "csv")


@dataclass
class Aplicacao:
    backend: str
    inventario: InventarioService
    service_desk: ServiceDesk
    conexao: Optional[IConexaoBD] = None

    def encerrar(self) -> None:
        if self.conexao is not None:
            self.conexao.desconectar()


def construir_aplicacao(
    backend: str = "sqlite",
    pasta_dados: str | Path = "dados",
    notificador: Optional[INotificavel] = None,
    caminho_db: Optional[str | Path] = None,
) -> Aplicacao:
    backend = backend.lower().strip()
    pasta = Path(pasta_dados)
    notificador = notificador or NotificadorConsole()

    if backend == "sqlite":
        conexao = ConexaoSQLite(caminho_db or pasta / "techlab.db")
        conexao.conectar()
        criar_schema(conexao)
        repo_ativos = AtivoRepository(conexao)
        repo_chamados = ChamadoRepository(conexao, repo_ativos)
    elif backend == "csv":
        conexao = None
        repo_ativos = AtivoCsvRepository(pasta / "ativos.csv")
        repo_chamados = ChamadoCsvRepository(pasta / "chamados.csv", repo_ativos)
    else:
        raise DadosInvalidosException(
            f"Backend desconhecido: {backend!r}. Use: {', '.join(BACKENDS)}."
        )

    inventario = InventarioService(repo_ativos, notificador)
    service_desk = ServiceDesk(repo_chamados, inventario, notificador)
    return Aplicacao(backend, inventario, service_desk, conexao)
