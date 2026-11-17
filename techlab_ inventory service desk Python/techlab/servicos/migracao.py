"""Migração de dados entre dois repositórios (ex.: CSV -> SQLite)."""

from __future__ import annotations

from techlab.dominio.ativo_ti import AtivoTI
from techlab.excecoes import PatrimonioDuplicadoException
from techlab.interfaces import IPersistencia


def migrar_ativos(
    origem: IPersistencia[AtivoTI], destino: IPersistencia[AtivoTI]
) -> tuple[int, int]:
    """Copia os ativos da origem para o destino.

    Devolve (migrados, ignorados). Ativos cujo patrimônio já existe no
    destino são ignorados, o que torna a migração segura para repetir.
    Os ids são gerados novamente pelo destino.
    """
    migrados = ignorados = 0
    for ativo in origem.listar():
        ativo.id = None
        try:
            destino.salvar(ativo)
            migrados += 1
        except PatrimonioDuplicadoException:
            ignorados += 1
    return migrados, ignorados
