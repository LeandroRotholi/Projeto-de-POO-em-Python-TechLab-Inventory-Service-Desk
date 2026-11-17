from __future__ import annotations

from typing import Any, Optional

from techlab.dominio import validacao
from techlab.dominio.ativo_ti import AtivoTI, StatusAtivo


class EstacaoTrabalho(AtivoTI):
    TIPO = "ESTACAO_TRABALHO"

    def __init__(
        self,
        codigo_patrimonio: str,
        modelo: str,
        data_aquisicao: Any,
        usuario_responsavel: str,
        setor: str,
        sistema_operacional: str,
        status: Any = StatusAtivo.ATIVO,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(codigo_patrimonio, modelo, data_aquisicao, status, id)
        self.usuario_responsavel = usuario_responsavel
        self.setor = setor
        self.sistema_operacional = sistema_operacional

    @property
    def usuario_responsavel(self) -> str:
        return self._usuario_responsavel

    @usuario_responsavel.setter
    def usuario_responsavel(self, valor: str) -> None:
        self._usuario_responsavel = validacao.texto_obrigatorio(
            valor, "usuário responsável", 100
        )

    @property
    def setor(self) -> str:
        return self._setor

    @setor.setter
    def setor(self, valor: str) -> None:
        self._setor = validacao.texto_obrigatorio(valor, "setor", 80)

    @property
    def sistema_operacional(self) -> str:
        return self._sistema_operacional

    @sistema_operacional.setter
    def sistema_operacional(self, valor: str) -> None:
        self._sistema_operacional = validacao.texto_obrigatorio(
            valor, "sistema operacional", 80
        )

    def atributos_especificos(self) -> dict[str, Any]:
        return {
            "usuario_responsavel": self._usuario_responsavel,
            "setor": self._setor,
            "sistema_operacional": self._sistema_operacional,
        }

    def vida_util_anos(self) -> int:
        return 4
