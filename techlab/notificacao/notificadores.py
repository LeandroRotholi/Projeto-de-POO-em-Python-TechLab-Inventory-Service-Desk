"""Implementações de INotificavel."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from techlab.excecoes import FalhaPersistenciaException
from techlab.interfaces import INotificavel


class NotificadorConsole(INotificavel):
    """Imprime as notificações no terminal."""

    def notificar(self, mensagem: str, nivel: str = "INFO") -> None:
        print(f"  [{nivel}] {mensagem}")


class NotificadorArquivo(INotificavel):
    """Acrescenta as notificações em um arquivo de log."""

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = Path(caminho)

    def notificar(self, mensagem: str, nivel: str = "INFO") -> None:
        carimbo = datetime.now().isoformat(timespec="seconds")
        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)
            with open(self._caminho, "a", encoding="utf-8") as arquivo:
                arquivo.write(f"{carimbo} [{nivel}] {mensagem}\n")
        except OSError as erro:
            raise FalhaPersistenciaException(
                f"Não foi possível gravar o log em {self._caminho}: {erro}"
            ) from erro
