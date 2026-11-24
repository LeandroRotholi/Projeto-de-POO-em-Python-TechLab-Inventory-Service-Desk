"""DTOs (Data Transfer Objects): estruturas simples para trafegar dados.

Um DTO não tem regras de negócio. Serve para exibir, filtrar em memória e
serializar (CSV) sem expor diretamente as entidades do domínio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from techlab.dominio.ativo_ti import AtivoTI
from techlab.dominio.chamado_suporte import ChamadoSuporte
from techlab.dominio.fabrica import ativo_de_dict
from techlab.excecoes import DadosInvalidosException


@dataclass(frozen=True)
class AtivoDTO:
    id: int | None
    tipo: str
    codigo_patrimonio: str
    modelo: str
    data_aquisicao: str
    status: str
    detalhes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def de_entidade(cls, ativo: AtivoTI) -> "AtivoDTO":
        return cls(**ativo.para_dict())

    def para_entidade(self) -> AtivoTI:
        return ativo_de_dict(self.para_dict())

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "codigo_patrimonio": self.codigo_patrimonio,
            "modelo": self.modelo,
            "data_aquisicao": self.data_aquisicao,
            "status": self.status,
            "detalhes": dict(self.detalhes),
        }

    # ---- formato plano para CSV (detalhes vira uma coluna JSON) ----
    def para_linha_csv(self) -> dict[str, Any]:
        linha = self.para_dict()
        linha["id"] = "" if self.id is None else self.id
        linha["detalhes"] = json.dumps(self.detalhes, ensure_ascii=False)
        return linha

    @classmethod
    def de_linha_csv(cls, linha: dict[str, str]) -> "AtivoDTO":
        try:
            detalhes = json.loads(linha.get("detalhes") or "{}")
            identificador = int(linha["id"]) if linha.get("id") else None
            return cls(
                id=identificador,
                tipo=linha["tipo"],
                codigo_patrimonio=linha["codigo_patrimonio"],
                modelo=linha["modelo"],
                data_aquisicao=linha["data_aquisicao"],
                status=linha["status"],
                detalhes=detalhes,
            )
        except (KeyError, ValueError, TypeError) as erro:
            raise DadosInvalidosException(f"Linha de CSV inválida: {erro}") from erro


@dataclass(frozen=True)
class ChamadoDTO:
    id: int | None
    titulo: str
    descricao: str
    prioridade: str
    status: str
    data_abertura: str
    ativo_id: int | None
    ativo_codigo: str

    @classmethod
    def de_entidade(cls, chamado: ChamadoSuporte) -> "ChamadoDTO":
        return cls(
            id=chamado.id,
            titulo=chamado.titulo,
            descricao=chamado.descricao,
            prioridade=chamado.prioridade.name,
            status=chamado.status.value,
            data_abertura=chamado.data_abertura.isoformat(),
            ativo_id=chamado.ativo_relacionado.id,
            ativo_codigo=chamado.ativo_relacionado.codigo_patrimonio,
        )
