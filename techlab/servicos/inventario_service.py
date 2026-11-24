"""Serviço de inventário: regras de negócio e coleções em memória.

Depende apenas das interfaces IPersistencia e INotificavel, por isso funciona
igualmente com CSV ou SQLite.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from typing import Any, Callable, Optional

from techlab.dominio.ativo_ti import AtivoTI, StatusAtivo
from techlab.dominio.fabrica import criar_ativo
from techlab.dto import AtivoDTO
from techlab.excecoes import DadosInvalidosException, EquipamentoNaoEncontradoException
from techlab.interfaces import INotificavel, IPersistencia

CHAVES_ORDENACAO: dict[str, Callable[[AtivoTI], Any]] = {
    "id": lambda a: a.id or 0,
    "codigo_patrimonio": lambda a: a.codigo_patrimonio,
    "modelo": lambda a: a.modelo.lower(),
    "data_aquisicao": lambda a: a.data_aquisicao,
    "status": lambda a: a.status.value,
    "tipo": lambda a: a.tipo,
}


class InventarioService:
    def __init__(
        self,
        repositorio: IPersistencia[AtivoTI],
        notificador: Optional[INotificavel] = None,
    ) -> None:
        self._repo = repositorio
        self._notificador = notificador

    def _avisar(self, mensagem: str, nivel: str = "INFO") -> None:
        if self._notificador is not None:
            self._notificador.notificar(mensagem, nivel)

    # ------------------------------ CRUD ------------------------------
    def cadastrar(self, ativo: AtivoTI) -> AtivoTI:
        salvo = self._repo.salvar(ativo)
        self._avisar(f"Equipamento {salvo.codigo_patrimonio} cadastrado (id {salvo.id}).")
        return salvo

    def cadastrar_novo(
        self, tipo: str, codigo_patrimonio: str, modelo: str, data_aquisicao: Any, **detalhes: Any
    ) -> AtivoTI:
        ativo = criar_ativo(tipo, codigo_patrimonio, modelo, data_aquisicao, **detalhes)
        return self.cadastrar(ativo)

    def obter(self, id: int) -> AtivoTI:
        return self._repo.buscar_por_id(id)

    def listar(self) -> list[AtivoTI]:
        return self._repo.listar()

    def atualizar(self, ativo: AtivoTI) -> AtivoTI:
        atualizado = self._repo.atualizar(ativo)
        self._avisar(f"Equipamento {atualizado.codigo_patrimonio} atualizado.")
        return atualizado

    def alterar_status(self, id: int, novo_status: Any) -> AtivoTI:
        ativo = self._repo.buscar_por_id(id)
        anterior = ativo.status
        ativo.status = novo_status
        self._repo.atualizar(ativo)
        self._avisar(
            f"Status de {ativo.codigo_patrimonio}: {anterior.value} -> {ativo.status.value}."
        )
        return ativo

    def remover(self, id: int) -> None:
        ativo = self._repo.buscar_por_id(id)
        self._repo.remover(id)
        self._avisar(f"Equipamento {ativo.codigo_patrimonio} removido.", "AVISO")

    # --------------------- coleções, filtros e buscas ---------------------
    def indexar_por_codigo(self) -> dict[str, AtivoTI]:
        """Mapa (dict) código de patrimônio -> ativo, com busca O(1)."""
        return {a.codigo_patrimonio: a for a in self.listar()}

    def buscar_por_codigo(self, codigo: str) -> AtivoTI:
        indice = self.indexar_por_codigo()
        chave = str(codigo).strip().upper()
        if chave not in indice:
            raise EquipamentoNaoEncontradoException(codigo)
        return indice[chave]

    def buscar_binaria_por_codigo(self, codigo: str) -> AtivoTI:
        """Busca binária sobre a lista ordenada por código de patrimônio."""
        ordenados = self.ordenar(self.listar(), "codigo_patrimonio")
        chave = str(codigo).strip().upper()
        posicao = bisect_left(ordenados, chave, key=lambda a: a.codigo_patrimonio)
        if posicao < len(ordenados) and ordenados[posicao].codigo_patrimonio == chave:
            return ordenados[posicao]
        raise EquipamentoNaoEncontradoException(codigo)

    def filtrar(
        self,
        tipo: Optional[str] = None,
        status: Any = None,
        termo_modelo: Optional[str] = None,
    ) -> list[AtivoTI]:
        resultado = self.listar()
        if tipo:
            alvo = tipo.strip().upper()
            resultado = [a for a in resultado if a.tipo == alvo]
        if status:
            alvo_status = StatusAtivo.de_valor(status)
            resultado = [a for a in resultado if a.status == alvo_status]
        if termo_modelo:
            termo = termo_modelo.strip().lower()
            resultado = [a for a in resultado if termo in a.modelo.lower()]
        return resultado

    @staticmethod
    def ordenar(
        ativos: list[AtivoTI], chave: str = "codigo_patrimonio", decrescente: bool = False
    ) -> list[AtivoTI]:
        if chave not in CHAVES_ORDENACAO:
            raise DadosInvalidosException(
                f"Chave de ordenação inválida: {chave!r}. "
                f"Opções: {', '.join(CHAVES_ORDENACAO)}."
            )
        return sorted(ativos, key=CHAVES_ORDENACAO[chave], reverse=decrescente)

    def agrupar_por_tipo(self) -> dict[str, list[AtivoTI]]:
        grupos: dict[str, list[AtivoTI]] = {}
        for ativo in self.listar():
            grupos.setdefault(ativo.tipo, []).append(ativo)
        return grupos

    def contar_por_status(self) -> dict[str, int]:
        return dict(Counter(a.status.value for a in self.listar()))

    def ativos_para_renovacao(self) -> list[AtivoTI]:
        """Equipamentos que atingiram a vida útil (exemplo de polimorfismo)."""
        return [a for a in self.listar() if a.precisa_renovacao() and a.status != StatusAtivo.DESCARTADO]

    def listar_dtos(self, ativos: Optional[list[AtivoTI]] = None) -> list[AtivoDTO]:
        base = self.listar() if ativos is None else ativos
        return [AtivoDTO.de_entidade(a) for a in base]

    # ------------------- intercâmbio entre repositórios -------------------
    def exportar_para(self, destino: IPersistencia[AtivoTI]) -> tuple[int, int]:
        """Copia o inventário atual para outro repositório (ex.: arquivo CSV)."""
        from techlab.servicos.migracao import migrar_ativos

        return migrar_ativos(self._repo, destino)

    def importar_de(self, origem: IPersistencia[AtivoTI]) -> tuple[int, int]:
        """Traz ativos de outro repositório (ex.: CSV) para o inventário atual."""
        from techlab.servicos.migracao import migrar_ativos

        resultado = migrar_ativos(origem, self._repo)
        self._avisar(f"Importação concluída: {resultado[0]} novo(s), {resultado[1]} ignorado(s).")
        return resultado
