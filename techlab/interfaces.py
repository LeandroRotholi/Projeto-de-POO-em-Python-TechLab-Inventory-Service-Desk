"""Contratos (interfaces) desacoplados do sistema.

As camadas superiores dependem apenas destas abstrações, nunca das
implementações concretas (CSV, SQLite, console...). Isso permite trocar
a persistência sem alterar a lógica de negócio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class IConexaoBD(ABC):
    """Contrato para qualquer conexão com banco de dados."""

    @abstractmethod
    def conectar(self) -> None:
        """Abre a conexão (não faz nada se já estiver aberta)."""

    @abstractmethod
    def desconectar(self) -> None:
        """Fecha a conexão."""

    @abstractmethod
    def obter_conexao(self) -> Any:
        """Devolve o objeto de conexão ativo ou lança FalhaConexaoBDException."""

    @property
    @abstractmethod
    def conectado(self) -> bool:
        """Indica se a conexão está aberta."""


class INotificavel(ABC):
    """Contrato para quem sabe emitir notificações (console, log, e-mail...)."""

    @abstractmethod
    def notificar(self, mensagem: str, nivel: str = "INFO") -> None:
        """Emite uma notificação."""


class IPersistencia(ABC, Generic[T]):
    """Contrato CRUD genérico para qualquer entidade."""

    @abstractmethod
    def salvar(self, entidade: T) -> T:
        """Create: grava uma nova entidade e devolve-a com o id preenchido."""

    @abstractmethod
    def buscar_por_id(self, id: int) -> T:
        """Read: devolve a entidade ou lança uma exceção de 'não encontrado'."""

    @abstractmethod
    def listar(self) -> list[T]:
        """Read: devolve todas as entidades."""

    @abstractmethod
    def atualizar(self, entidade: T) -> T:
        """Update: regrava uma entidade existente."""

    @abstractmethod
    def remover(self, id: int) -> None:
        """Delete: remove a entidade pelo id."""
