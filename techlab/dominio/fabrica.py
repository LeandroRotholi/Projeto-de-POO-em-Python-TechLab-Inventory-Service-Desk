"""Fábrica de ativos: cria a subclasse correta a partir do nome do tipo."""

from __future__ import annotations

from typing import Any, Optional

from techlab.dominio.ativo_ti import AtivoTI, StatusAtivo
from techlab.dominio.dispositivo_rede import DispositivoRede
from techlab.dominio.estacao_trabalho import EstacaoTrabalho
from techlab.dominio.servidor import Servidor
from techlab.dominio.validacao import normalizar
from techlab.excecoes import DadosInvalidosException

_CLASSES: dict[str, type[AtivoTI]] = {
    cls.TIPO: cls for cls in (Servidor, EstacaoTrabalho, DispositivoRede)
}


def tipos_disponiveis() -> list[str]:
    return list(_CLASSES)


def criar_ativo(
    tipo: str,
    codigo_patrimonio: str,
    modelo: str,
    data_aquisicao: Any,
    status: Any = StatusAtivo.ATIVO,
    id: Optional[int] = None,
    **detalhes: Any,
) -> AtivoTI:
    chave = normalizar(tipo).replace(" ", "_")
    classe = _CLASSES.get(chave)
    if classe is None:
        raise DadosInvalidosException(
            f"Tipo de ativo desconhecido: {tipo!r}. "
            f"Tipos aceitos: {', '.join(_CLASSES)}."
        )
    try:
        return classe(
            codigo_patrimonio=codigo_patrimonio,
            modelo=modelo,
            data_aquisicao=data_aquisicao,
            status=status,
            id=id,
            **detalhes,
        )
    except TypeError as erro:
        raise DadosInvalidosException(
            f"Atributos incorretos para o tipo {chave}: {erro}"
        ) from erro


def ativo_de_dict(dados: dict[str, Any]) -> AtivoTI:
    """Reconstrói um ativo a partir do formato gerado por ``AtivoTI.para_dict``."""
    try:
        return criar_ativo(
            tipo=dados["tipo"],
            codigo_patrimonio=dados["codigo_patrimonio"],
            modelo=dados["modelo"],
            data_aquisicao=dados["data_aquisicao"],
            status=dados.get("status", StatusAtivo.ATIVO),
            id=dados.get("id") or None,
            **(dados.get("detalhes") or {}),
        )
    except KeyError as erro:
        raise DadosInvalidosException(f"Campo ausente: {erro}") from erro
