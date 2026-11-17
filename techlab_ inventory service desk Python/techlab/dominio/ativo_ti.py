"""Classe abstrata base de todos os equipamentos de TI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from typing import Any, Optional

from techlab.dominio import validacao
from techlab.excecoes import DadosInvalidosException


class StatusAtivo(str, Enum):
    ATIVO = "ATIVO"
    EM_MANUTENCAO = "EM_MANUTENCAO"
    INATIVO = "INATIVO"
    DESCARTADO = "DESCARTADO"

    @classmethod
    def de_valor(cls, valor: Any) -> "StatusAtivo":
        if isinstance(valor, cls):
            return valor
        texto = validacao.normalizar(valor).replace(" ", "_")
        try:
            return cls(texto)
        except ValueError:
            validos = ", ".join(s.value for s in cls)
            raise DadosInvalidosException(
                f"Status inválido: {valor!r}. Valores aceitos: {validos}."
            )


class AtivoTI(ABC):
    """Ativo de TI genérico.

    Atributos obrigatórios (privados, expostos por properties):
    id, codigo_patrimonio, modelo, data_aquisicao e status.
    Subclasses acrescentam atributos próprios e implementam os métodos
    abstratos, o que torna impossível instanciar AtivoTI diretamente.
    """

    TIPO: str = ""

    def __init__(
        self,
        codigo_patrimonio: str,
        modelo: str,
        data_aquisicao: Any,
        status: Any = StatusAtivo.ATIVO,
        id: Optional[int] = None,
    ) -> None:
        self._id: Optional[int] = None
        self._codigo_patrimonio: str = ""
        self._modelo: str = ""
        self._data_aquisicao: date = date.today()
        self._status: StatusAtivo = StatusAtivo.ATIVO

        self.id = id
        self.codigo_patrimonio = codigo_patrimonio
        self.modelo = modelo
        self.data_aquisicao = data_aquisicao
        self.status = status

    # ---------- encapsulamento: getters e setters com validação ----------
    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, valor: Optional[int]) -> None:
        self._id = None if valor is None else validacao.inteiro_positivo(valor, "id")

    @property
    def codigo_patrimonio(self) -> str:
        return self._codigo_patrimonio

    @codigo_patrimonio.setter
    def codigo_patrimonio(self, valor: str) -> None:
        self._codigo_patrimonio = validacao.texto_obrigatorio(
            valor, "código de patrimônio", 50
        ).upper()

    @property
    def modelo(self) -> str:
        return self._modelo

    @modelo.setter
    def modelo(self, valor: str) -> None:
        self._modelo = validacao.texto_obrigatorio(valor, "modelo", 100)

    @property
    def data_aquisicao(self) -> date:
        return self._data_aquisicao

    @data_aquisicao.setter
    def data_aquisicao(self, valor: Any) -> None:
        data = validacao.converter_data(valor, "data de aquisição")
        if data > date.today():
            raise DadosInvalidosException(
                "A data de aquisição não pode estar no futuro."
            )
        self._data_aquisicao = data

    @property
    def status(self) -> StatusAtivo:
        return self._status

    @status.setter
    def status(self, valor: Any) -> None:
        self._status = StatusAtivo.de_valor(valor)

    @property
    def tipo(self) -> str:
        return type(self).TIPO

    # ---------- comportamento específico (polimorfismo) ----------
    @abstractmethod
    def atributos_especificos(self) -> dict[str, Any]:
        """Atributos próprios da subclasse, prontos para serializar."""

    @abstractmethod
    def vida_util_anos(self) -> int:
        """Vida útil recomendada do tipo de equipamento, em anos."""

    # ---------- comportamento comum ----------
    def idade_anos(self, hoje: Optional[date] = None) -> int:
        hoje = hoje or date.today()
        d = self._data_aquisicao
        return hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))

    def precisa_renovacao(self, hoje: Optional[date] = None) -> bool:
        return self.idade_anos(hoje) >= self.vida_util_anos()

    def descricao_detalhada(self) -> str:
        extras = ", ".join(f"{k}={v}" for k, v in self.atributos_especificos().items())
        return (
            f"[{self.tipo}] {self.codigo_patrimonio} - {self.modelo} | "
            f"adquirido em {self._data_aquisicao.isoformat()} | "
            f"status {self._status.value} | {extras}"
        )

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "tipo": self.tipo,
            "codigo_patrimonio": self._codigo_patrimonio,
            "modelo": self._modelo,
            "data_aquisicao": self._data_aquisicao.isoformat(),
            "status": self._status.value,
            "detalhes": self.atributos_especificos(),
        }

    def __str__(self) -> str:
        return self.descricao_detalhada()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self._id!r}, "
            f"codigo_patrimonio={self._codigo_patrimonio!r})"
        )
