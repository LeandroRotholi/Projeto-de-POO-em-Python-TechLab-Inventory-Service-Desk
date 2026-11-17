from __future__ import annotations

from typing import Any, Optional

from techlab.dominio import validacao
from techlab.dominio.ativo_ti import AtivoTI, StatusAtivo


class DispositivoRede(AtivoTI):
    TIPO = "DISPOSITIVO_REDE"

    def __init__(
        self,
        codigo_patrimonio: str,
        modelo: str,
        data_aquisicao: Any,
        tipo_dispositivo: str,
        endereco_ip: str,
        numero_portas: int,
        status: Any = StatusAtivo.ATIVO,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(codigo_patrimonio, modelo, data_aquisicao, status, id)
        self.tipo_dispositivo = tipo_dispositivo
        self.endereco_ip = endereco_ip
        self.numero_portas = numero_portas

    @property
    def tipo_dispositivo(self) -> str:
        return self._tipo_dispositivo

    @tipo_dispositivo.setter
    def tipo_dispositivo(self, valor: str) -> None:
        self._tipo_dispositivo = validacao.texto_obrigatorio(
            valor, "tipo do dispositivo", 50
        ).lower()

    @property
    def endereco_ip(self) -> str:
        return self._endereco_ip

    @endereco_ip.setter
    def endereco_ip(self, valor: str) -> None:
        self._endereco_ip = validacao.endereco_ip(valor, "endereço IP")

    @property
    def numero_portas(self) -> int:
        return self._numero_portas

    @numero_portas.setter
    def numero_portas(self, valor: int) -> None:
        self._numero_portas = validacao.inteiro_positivo(valor, "número de portas")

    def atributos_especificos(self) -> dict[str, Any]:
        return {
            "tipo_dispositivo": self._tipo_dispositivo,
            "endereco_ip": self._endereco_ip,
            "numero_portas": self._numero_portas,
        }

    def vida_util_anos(self) -> int:
        return 7
