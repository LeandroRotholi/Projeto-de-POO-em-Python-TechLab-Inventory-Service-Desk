"""Serviço de chamados de suporte (Service Desk)."""

from __future__ import annotations

from typing import Any, Optional

from techlab.dominio.ativo_ti import StatusAtivo
from techlab.dominio.chamado_suporte import ChamadoSuporte, Prioridade, StatusChamado
from techlab.dto import ChamadoDTO
from techlab.interfaces import INotificavel, IPersistencia
from techlab.servicos.inventario_service import InventarioService


class ServiceDesk:
    def __init__(
        self,
        repositorio: IPersistencia[ChamadoSuporte],
        inventario: InventarioService,
        notificador: Optional[INotificavel] = None,
    ) -> None:
        self._repo = repositorio
        self._inventario = inventario
        self._notificador = notificador

    def _avisar(self, mensagem: str, nivel: str = "INFO") -> None:
        if self._notificador is not None:
            self._notificador.notificar(mensagem, nivel)

    def abrir_chamado(
        self, titulo: str, descricao: str, prioridade: Any, ativo_id: int
    ) -> ChamadoSuporte:
        ativo = self._inventario.obter(ativo_id)  # lança EquipamentoNaoEncontradoException
        chamado = ChamadoSuporte(titulo, descricao, prioridade, ativo)
        self._repo.salvar(chamado)
        nivel = "ALERTA" if chamado.prioridade == Prioridade.CRITICA else "INFO"
        self._avisar(
            f"Chamado #{chamado.id} aberto ({chamado.prioridade.name}) para {ativo.codigo_patrimonio}.",
            nivel,
        )
        # Regra de negócio: chamado crítico tira o equipamento de operação.
        if chamado.prioridade == Prioridade.CRITICA and ativo.status == StatusAtivo.ATIVO:
            self._inventario.alterar_status(ativo.id, StatusAtivo.EM_MANUTENCAO)
        return chamado

    def obter(self, id: int) -> ChamadoSuporte:
        return self._repo.buscar_por_id(id)

    def listar(
        self, status: Any = None, por_prioridade: bool = True
    ) -> list[ChamadoSuporte]:
        chamados = self._repo.listar()
        if status:
            alvo = StatusChamado.de_valor(status)
            chamados = [c for c in chamados if c.status == alvo]
        if por_prioridade:
            # mais urgentes primeiro; empate resolvido pelo mais antigo
            chamados = sorted(chamados, key=lambda c: (-int(c.prioridade), c.data_abertura))
        return chamados

    def chamados_do_ativo(self, ativo_id: int) -> list[ChamadoSuporte]:
        return [c for c in self._repo.listar() if c.ativo_relacionado.id == ativo_id]

    def iniciar_atendimento(self, id: int) -> ChamadoSuporte:
        chamado = self._repo.buscar_por_id(id)
        chamado.iniciar_atendimento()
        self._repo.atualizar(chamado)
        self._avisar(f"Chamado #{id} em atendimento.")
        return chamado

    def fechar_chamado(self, id: int) -> ChamadoSuporte:
        chamado = self._repo.buscar_por_id(id)
        chamado.fechar()
        self._repo.atualizar(chamado)
        self._avisar(f"Chamado #{id} fechado.")
        # Se era o último chamado aberto do equipamento em manutenção, ele volta a operar.
        ativo = self._inventario.obter(chamado.ativo_relacionado.id)
        ainda_abertos = [
            c for c in self.chamados_do_ativo(ativo.id) if c.aberto and c.id != chamado.id
        ]
        if ativo.status == StatusAtivo.EM_MANUTENCAO and not ainda_abertos:
            self._inventario.alterar_status(ativo.id, StatusAtivo.ATIVO)
        return chamado

    def contar_por_prioridade(self) -> dict[str, int]:
        contagem = {p.name: 0 for p in Prioridade}
        for chamado in self._repo.listar():
            if chamado.aberto:
                contagem[chamado.prioridade.name] += 1
        return contagem

    def listar_dtos(self, chamados: Optional[list[ChamadoSuporte]] = None) -> list[ChamadoDTO]:
        base = self.listar() if chamados is None else chamados
        return [ChamadoDTO.de_entidade(c) for c in base]
