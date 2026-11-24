from __future__ import annotations

from typing import Any, Optional

from techlab.dominio import validacao
from techlab.dominio.ativo_ti import AtivoTI, StatusAtivo


class Servidor(AtivoTI):
    TIPO = "SERVIDOR"

    def __init__(
        self,
        codigo_patrimonio: str,
        modelo: str,
        data_aquisicao: Any,
        ip: str,
        sistema_operacional: str,
        memoria_gb: int,
        num_cpus: int,
        status: Any = StatusAtivo.ATIVO,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(codigo_patrimonio, modelo, data_aquisicao, status, id)
        self.ip = ip
        self.sistema_operacional = sistema_operacional
        self.memoria_gb = memoria_gb
        self.num_cpus = num_cpus

    @property
    def ip(self) -> str:
        return self._ip

    @ip.setter
    def ip(self, valor: str) -> None:
        self._ip = validacao.endereco_ip(valor)

    @property
    def sistema_operacional(self) -> str:
        return self._sistema_operacional

    @sistema_operacional.setter
    def sistema_operacional(self, valor: str) -> None:
        self._sistema_operacional = validacao.texto_obrigatorio(
            valor, "sistema operacional", 80
        )

    @property
    def memoria_gb(self) -> int:
        return self._memoria_gb

    @memoria_gb.setter
    def memoria_gb(self, valor: int) -> None:
        self._memoria_gb = validacao.inteiro_positivo(valor, "memória (GB)")

    @property
    def num_cpus(self) -> int:
        return self._num_cpus

    @num_cpus.setter
    def num_cpus(self, valor: int) -> None:
        self._num_cpus = validacao.inteiro_positivo(valor, "número de CPUs")

    def atributos_especificos(self) -> dict[str, Any]:
        return {
            "ip": self._ip,
            "sistema_operacional": self._sistema_operacional,
            "memoria_gb": self._memoria_gb,
            "num_cpus": self._num_cpus,
        }

    def vida_util_anos(self) -> int:
        return 5
