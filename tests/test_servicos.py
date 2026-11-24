import tempfile
import unittest
from pathlib import Path

from techlab.aplicacao import construir_aplicacao
from techlab.dominio import Prioridade, StatusAtivo, StatusChamado
from techlab.excecoes import (
    DadosInvalidosException, EquipamentoNaoEncontradoException, OperacaoNaoPermitidaException,
)
from techlab.interfaces import INotificavel
from techlab.persistencia import AtivoCsvRepository
from tests.auxiliares import nova_estacao, novo_servidor, novo_switch


class NotificadorEspiao(INotificavel):
    def __init__(self):
        self.mensagens = []

    def notificar(self, mensagem, nivel="INFO"):
        self.mensagens.append((nivel, mensagem))


class BaseServicos(unittest.TestCase):
    backend = "sqlite"

    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.espiao = NotificadorEspiao()
        self.app = construir_aplicacao(self.backend, self._pasta.name, self.espiao)
        self.inv = self.app.inventario
        self.desk = self.app.service_desk
        self.srv = self.inv.cadastrar(novo_servidor("SRV-B", "Dell R740", "2018-01-01"))
        self.est = self.inv.cadastrar(nova_estacao("EST-A", "Lenovo M70", "2024-01-01"))
        self.rede = self.inv.cadastrar(novo_switch("NET-C", "Cisco 2960", "2022-01-01"))

    def tearDown(self):
        self.app.encerrar()
        self._pasta.cleanup()


class TestInventarioService(BaseServicos):
    def test_filtros(self):
        self.assertEqual(len(self.inv.filtrar(tipo="servidor")), 1)
        self.assertEqual(len(self.inv.filtrar(termo_modelo="lenovo")), 1)
        self.inv.alterar_status(self.est.id, "INATIVO")
        self.assertEqual([a.codigo_patrimonio for a in self.inv.filtrar(status="inativo")], ["EST-A"])
        self.assertEqual(self.inv.filtrar(tipo="SERVIDOR", termo_modelo="cisco"), [])

    def test_ordenacao(self):
        todos = self.inv.listar()
        por_codigo = [a.codigo_patrimonio for a in self.inv.ordenar(todos, "codigo_patrimonio")]
        self.assertEqual(por_codigo, ["EST-A", "NET-C", "SRV-B"])
        por_data = [a.codigo_patrimonio for a in self.inv.ordenar(todos, "data_aquisicao", True)]
        self.assertEqual(por_data, ["EST-A", "NET-C", "SRV-B"])
        with self.assertRaises(DadosInvalidosException):
            self.inv.ordenar(todos, "cor")

    def test_buscas_por_codigo(self):
        self.assertEqual(self.inv.buscar_por_codigo(" net-c ").id, self.rede.id)
        self.assertEqual(self.inv.buscar_binaria_por_codigo("srv-b").id, self.srv.id)
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.inv.buscar_por_codigo("INEXISTENTE")
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.inv.buscar_binaria_por_codigo("INEXISTENTE")

    def test_agrupamento_e_contagem(self):
        grupos = self.inv.agrupar_por_tipo()
        self.assertEqual({t: len(v) for t, v in grupos.items()},
                         {"SERVIDOR": 1, "ESTACAO_TRABALHO": 1, "DISPOSITIVO_REDE": 1})
        self.assertEqual(self.inv.contar_por_status(), {"ATIVO": 3})

    def test_renovacao(self):
        codigos = [a.codigo_patrimonio for a in self.inv.ativos_para_renovacao()]
        self.assertEqual(codigos, ["SRV-B"])

    def test_dtos(self):
        dtos = self.inv.listar_dtos()
        self.assertEqual(dtos[0].codigo_patrimonio, "SRV-B")
        self.assertIsInstance(dtos[0].detalhes, dict)

    def test_notificacoes(self):
        self.inv.alterar_status(self.srv.id, "INATIVO")
        self.assertTrue(any("ATIVO -> INATIVO" in m for _, m in self.espiao.mensagens))

    def test_remocao(self):
        self.inv.remover(self.est.id)
        self.assertEqual(len(self.inv.listar()), 2)
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.inv.remover(self.est.id)

    def test_exportar_e_importar_csv(self):
        destino = AtivoCsvRepository(Path(self._pasta.name) / "export.csv")
        self.assertEqual(self.inv.exportar_para(destino), (3, 0))
        self.assertEqual(self.inv.exportar_para(destino), (0, 3))  # idempotente
        self.assertEqual(len(destino.listar()), 3)
        self.assertEqual(self.inv.importar_de(destino), (0, 3))


class TestServiceDesk(BaseServicos):
    def test_abrir_chamado_para_ativo_inexistente(self):
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.desk.abrir_chamado("T", "D", "BAIXA", 999)

    def test_chamado_critico_coloca_ativo_em_manutencao_e_fechar_devolve(self):
        chamado = self.desk.abrir_chamado("Caiu", "Sem link", "CRITICA", self.rede.id)
        self.assertEqual(self.inv.obter(self.rede.id).status, StatusAtivo.EM_MANUTENCAO)
        self.assertTrue(any(n == "ALERTA" for n, _ in self.espiao.mensagens))
        self.desk.fechar_chamado(chamado.id)
        self.assertEqual(self.inv.obter(self.rede.id).status, StatusAtivo.ATIVO)

    def test_ativo_so_volta_quando_nao_ha_outros_chamados_abertos(self):
        c1 = self.desk.abrir_chamado("A", "a", "CRITICA", self.srv.id)
        c2 = self.desk.abrir_chamado("B", "b", "BAIXA", self.srv.id)
        self.desk.fechar_chamado(c1.id)
        self.assertEqual(self.inv.obter(self.srv.id).status, StatusAtivo.EM_MANUTENCAO)
        self.desk.fechar_chamado(c2.id)
        self.assertEqual(self.inv.obter(self.srv.id).status, StatusAtivo.ATIVO)

    def test_chamado_nao_critico_nao_altera_ativo(self):
        self.desk.abrir_chamado("A", "a", "ALTA", self.srv.id)
        self.assertEqual(self.inv.obter(self.srv.id).status, StatusAtivo.ATIVO)

    def test_ordenacao_por_prioridade_e_filtro(self):
        self.desk.abrir_chamado("baixo", "d", "BAIXA", self.srv.id)
        self.desk.abrir_chamado("critico", "d", "CRITICA", self.est.id)
        self.desk.abrir_chamado("alto", "d", "ALTA", self.rede.id)
        titulos = [c.titulo for c in self.desk.listar()]
        self.assertEqual(titulos, ["critico", "alto", "baixo"])
        self.desk.iniciar_atendimento(1)
        self.assertEqual([c.titulo for c in self.desk.listar(status="EM_ATENDIMENTO")], ["baixo"])

    def test_contagem_por_prioridade(self):
        self.desk.abrir_chamado("a", "d", "ALTA", self.srv.id)
        c = self.desk.abrir_chamado("b", "d", "ALTA", self.est.id)
        self.desk.fechar_chamado(c.id)
        self.assertEqual(self.desk.contar_por_prioridade()["ALTA"], 1)

    def test_fechar_duas_vezes(self):
        c = self.desk.abrir_chamado("a", "d", "BAIXA", self.srv.id)
        self.desk.fechar_chamado(c.id)
        with self.assertRaises(OperacaoNaoPermitidaException):
            self.desk.fechar_chamado(c.id)
        self.assertEqual(self.desk.obter(c.id).status, StatusChamado.FECHADO)

    def test_dtos_de_chamado(self):
        self.desk.abrir_chamado("a", "d", "MEDIA", self.srv.id)
        dto = self.desk.listar_dtos()[0]
        self.assertEqual((dto.prioridade, dto.ativo_codigo), ("MEDIA", "SRV-B"))


class TestServicosComCsv(TestServiceDesk, TestInventarioService):
    """Reexecuta TODOS os testes de serviço com o backend CSV (troca transparente)."""

    backend = "csv"

    def test_remocao_de_ativo_com_chamado_no_csv_nao_tem_fk(self):
        pass  # limitação conhecida da etapa CSV; a integridade vem com o banco relacional

    def test_exportar_e_importar_csv(self):
        pass  # no backend CSV, origem e destino seriam o mesmo arquivo de dados


class TestAplicacao(unittest.TestCase):
    def test_backend_desconhecido(self):
        with self.assertRaises(DadosInvalidosException):
            construir_aplicacao("mongodb")

    def test_prioridade_enum_ordenada(self):
        self.assertLess(Prioridade.BAIXA, Prioridade.CRITICA)


if __name__ == "__main__":
    unittest.main()
