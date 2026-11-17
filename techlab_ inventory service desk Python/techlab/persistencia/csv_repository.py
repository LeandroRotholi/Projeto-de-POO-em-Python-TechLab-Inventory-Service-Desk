"""Persistência inicial em arquivos CSV (etapa anterior ao banco de dados).

Cada operação lê o arquivo inteiro, altera a lista em memória e regrava o
arquivo de forma atômica (arquivo temporário + os.replace), evitando deixar
o CSV corrompido caso algo falhe no meio da escrita.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from techlab.dominio.ativo_ti import AtivoTI
from techlab.dominio.chamado_suporte import ChamadoSuporte
from techlab.dto import AtivoDTO
from techlab.excecoes import (
    ChamadoNaoEncontradoException,
    DadosInvalidosException,
    EquipamentoNaoEncontradoException,
    FalhaPersistenciaException,
    PatrimonioDuplicadoException,
    TechLabError,
)
from techlab.interfaces import IPersistencia


def _ler_linhas(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    try:
        with open(caminho, newline="", encoding="utf-8") as arquivo:
            return list(csv.DictReader(arquivo))
    except (OSError, csv.Error, UnicodeDecodeError) as erro:
        raise FalhaPersistenciaException(f"Erro ao ler {caminho}: {erro}") from erro


def _gravar_linhas(
    caminho: Path, campos: list[str], linhas: list[dict[str, object]]
) -> None:
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(temporario, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos)
            escritor.writeheader()
            escritor.writerows(linhas)
        os.replace(temporario, caminho)
    except OSError as erro:
        raise FalhaPersistenciaException(f"Erro ao gravar {caminho}: {erro}") from erro


class AtivoCsvRepository(IPersistencia[AtivoTI]):
    CAMPOS = ["id", "tipo", "codigo_patrimonio", "modelo", "data_aquisicao", "status", "detalhes"]

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = Path(caminho)

    def _carregar(self) -> list[AtivoTI]:
        ativos = []
        for numero, linha in enumerate(_ler_linhas(self._caminho), start=2):
            try:
                ativos.append(AtivoDTO.de_linha_csv(linha).para_entidade())
            except TechLabError as erro:
                raise FalhaPersistenciaException(
                    f"Linha {numero} de {self._caminho} está inválida: {erro}"
                ) from erro
        return ativos

    def _gravar(self, ativos: list[AtivoTI]) -> None:
        linhas = [AtivoDTO.de_entidade(a).para_linha_csv() for a in ativos]
        _gravar_linhas(self._caminho, self.CAMPOS, linhas)

    def salvar(self, ativo: AtivoTI) -> AtivoTI:
        ativos = self._carregar()
        if any(a.codigo_patrimonio == ativo.codigo_patrimonio for a in ativos):
            raise PatrimonioDuplicadoException(ativo.codigo_patrimonio)
        ativo.id = max((a.id or 0 for a in ativos), default=0) + 1
        ativos.append(ativo)
        self._gravar(ativos)
        return ativo

    def buscar_por_id(self, id: int) -> AtivoTI:
        for ativo in self._carregar():
            if ativo.id == id:
                return ativo
        raise EquipamentoNaoEncontradoException(id)

    def listar(self) -> list[AtivoTI]:
        return self._carregar()

    def atualizar(self, ativo: AtivoTI) -> AtivoTI:
        if ativo.id is None:
            raise DadosInvalidosException("Não é possível atualizar um ativo sem id.")
        ativos = self._carregar()
        for posicao, existente in enumerate(ativos):
            if existente.id == ativo.id:
                for outro in ativos:
                    if outro.id != ativo.id and outro.codigo_patrimonio == ativo.codigo_patrimonio:
                        raise PatrimonioDuplicadoException(ativo.codigo_patrimonio)
                ativos[posicao] = ativo
                self._gravar(ativos)
                return ativo
        raise EquipamentoNaoEncontradoException(ativo.id)

    def remover(self, id: int) -> None:
        ativos = self._carregar()
        restantes = [a for a in ativos if a.id != id]
        if len(restantes) == len(ativos):
            raise EquipamentoNaoEncontradoException(id)
        self._gravar(restantes)


class ChamadoCsvRepository(IPersistencia[ChamadoSuporte]):
    CAMPOS = ["id", "titulo", "descricao", "prioridade", "data_abertura", "status", "ativo_id"]

    def __init__(self, caminho: str | Path, repositorio_ativos: IPersistencia[AtivoTI]) -> None:
        self._caminho = Path(caminho)
        self._ativos = repositorio_ativos

    def _carregar(self) -> list[ChamadoSuporte]:
        mapa_ativos = {a.id: a for a in self._ativos.listar()}
        chamados = []
        for numero, linha in enumerate(_ler_linhas(self._caminho), start=2):
            try:
                ativo_id = int(linha["ativo_id"])
                if ativo_id not in mapa_ativos:
                    raise EquipamentoNaoEncontradoException(ativo_id)
                chamados.append(
                    ChamadoSuporte(
                        id=int(linha["id"]),
                        titulo=linha["titulo"],
                        descricao=linha["descricao"],
                        prioridade=linha["prioridade"],
                        ativo_relacionado=mapa_ativos[ativo_id],
                        data_abertura=linha["data_abertura"],
                        status=linha["status"],
                    )
                )
            except (TechLabError, KeyError, ValueError) as erro:
                raise FalhaPersistenciaException(
                    f"Linha {numero} de {self._caminho} está inválida: {erro}"
                ) from erro
        return chamados

    def _gravar(self, chamados: list[ChamadoSuporte]) -> None:
        linhas = [
            {
                "id": c.id,
                "titulo": c.titulo,
                "descricao": c.descricao,
                "prioridade": c.prioridade.name,
                "data_abertura": c.data_abertura.isoformat(),
                "status": c.status.value,
                "ativo_id": c.ativo_relacionado.id,
            }
            for c in chamados
        ]
        _gravar_linhas(self._caminho, self.CAMPOS, linhas)

    def salvar(self, chamado: ChamadoSuporte) -> ChamadoSuporte:
        if chamado.ativo_relacionado.id is None:
            raise DadosInvalidosException(
                "O equipamento do chamado precisa estar cadastrado (sem id)."
            )
        self._ativos.buscar_por_id(chamado.ativo_relacionado.id)  # valida existência
        chamados = self._carregar()
        chamado.id = max((c.id or 0 for c in chamados), default=0) + 1
        chamados.append(chamado)
        self._gravar(chamados)
        return chamado

    def buscar_por_id(self, id: int) -> ChamadoSuporte:
        for chamado in self._carregar():
            if chamado.id == id:
                return chamado
        raise ChamadoNaoEncontradoException(id)

    def listar(self) -> list[ChamadoSuporte]:
        return self._carregar()

    def listar_por_ativo(self, ativo_id: int) -> list[ChamadoSuporte]:
        return [c for c in self._carregar() if c.ativo_relacionado.id == ativo_id]

    def atualizar(self, chamado: ChamadoSuporte) -> ChamadoSuporte:
        if chamado.id is None:
            raise DadosInvalidosException("Não é possível atualizar um chamado sem id.")
        chamados = self._carregar()
        for posicao, existente in enumerate(chamados):
            if existente.id == chamado.id:
                chamados[posicao] = chamado
                self._gravar(chamados)
                return chamado
        raise ChamadoNaoEncontradoException(chamado.id)

    def remover(self, id: int) -> None:
        chamados = self._carregar()
        restantes = [c for c in chamados if c.id != id]
        if len(restantes) == len(chamados):
            raise ChamadoNaoEncontradoException(id)
        self._gravar(restantes)
