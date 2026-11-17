"""Entidade de negócio: chamado de suporte técnico."""

from __future__ import annotations

from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Optional

from techlab.dominio import validacao
from techlab.dominio.ativo_ti import AtivoTI
from techlab.excecoes import DadosInvalidosException, OperacaoNaoPermitidaException


class Prioridade(IntEnum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4

    @classmethod
    def de_valor(cls, valor: Any) -> "Prioridade":
        if isinstance(valor, cls):
            return valor
        texto = validacao.normalizar(valor)
        try:
            if texto.isdigit():
                return cls(int(texto))
            return cls[texto]
        except (ValueError, KeyError):
            validos = ", ".join(p.name for p in cls)
            raise DadosInvalidosException(
                f"Prioridade inválida: {valor!r}. Valores aceitos: {validos}."
            )


class StatusChamado(str, Enum):
    ABERTO = "ABERTO"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    FECHADO = "FECHADO"

    @classmethod
    def de_valor(cls, valor: Any) -> "StatusChamado":
        if isinstance(valor, cls):
            return valor
        try:
            return cls(validacao.normalizar(valor).replace(" ", "_"))
        except ValueError:
            raise DadosInvalidosException(f"Status de chamado inválido: {valor!r}.")


class ChamadoSuporte:
    """Chamado vinculado diretamente a um equipamento (AtivoTI)."""

    def __init__(
        self,
        titulo: str,
        descricao: str,
        prioridade: Any,
        ativo_relacionado: AtivoTI,
        data_abertura: Any = None,
        status: Any = StatusChamado.ABERTO,
        id: Optional[int] = None,
    ) -> None:
        self._id: Optional[int] = None
        self.id = id
        self.titulo = titulo
        self.descricao = descricao
        self.prioridade = prioridade
        self.ativo_relacionado = ativo_relacionado
        self._data_abertura = (
            validacao.converter_datahora(data_abertura, "data de abertura")
            if data_abertura is not None
            else datetime.now().replace(microsecond=0)
        )
        self.status = status

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, valor: Optional[int]) -> None:
        self._id = None if valor is None else validacao.inteiro_positivo(valor, "id")

    @property
    def titulo(self) -> str:
        return self._titulo

    @titulo.setter
    def titulo(self, valor: str) -> None:
        self._titulo = validacao.texto_obrigatorio(valor, "título", 120)

    @property
    def descricao(self) -> str:
        return self._descricao

    @descricao.setter
    def descricao(self, valor: str) -> None:
        self._descricao = validacao.texto_obrigatorio(valor, "descrição", 2000)

    @property
    def prioridade(self) -> Prioridade:
        return self._prioridade

    @prioridade.setter
    def prioridade(self, valor: Any) -> None:
        self._prioridade = Prioridade.de_valor(valor)

    @property
    def data_abertura(self) -> datetime:
        return self._data_abertura

    @property
    def ativo_relacionado(self) -> AtivoTI:
        return self._ativo_relacionado

    @ativo_relacionado.setter
    def ativo_relacionado(self, valor: AtivoTI) -> None:
        if not isinstance(valor, AtivoTI):
            raise DadosInvalidosException(
                "O chamado precisa estar associado a um equipamento válido."
            )
        self._ativo_relacionado = valor

    @property
    def status(self) -> StatusChamado:
        return self._status

    @status.setter
    def status(self, valor: Any) -> None:
        self._status = StatusChamado.de_valor(valor)

    # ---------- regras de negócio ----------
    def iniciar_atendimento(self) -> None:
        if self._status != StatusChamado.ABERTO:
            raise OperacaoNaoPermitidaException(
                "Só é possível iniciar o atendimento de um chamado aberto."
            )
        self._status = StatusChamado.EM_ATENDIMENTO

    def fechar(self) -> None:
        if self._status == StatusChamado.FECHADO:
            raise OperacaoNaoPermitidaException("O chamado já está fechado.")
        self._status = StatusChamado.FECHADO

    @property
    def aberto(self) -> bool:
        return self._status != StatusChamado.FECHADO

    def __str__(self) -> str:
        return (
            f"#{self._id} [{self._prioridade.name}] {self._titulo} "
            f"({self._status.value}) - equipamento {self._ativo_relacionado.codigo_patrimonio} "
            f"- aberto em {self._data_abertura.strftime('%d/%m/%Y %H:%M')}"
        )

    def __repr__(self) -> str:
        return f"ChamadoSuporte(id={self._id!r}, titulo={self._titulo!r})"
