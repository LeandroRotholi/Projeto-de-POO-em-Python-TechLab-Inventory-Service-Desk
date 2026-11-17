import tempfile
import unittest
from pathlib import Path

from techlab.dominio import ChamadoSuporte
from techlab.excecoes import (
    ChamadoNaoEncontradoException, EquipamentoNaoEncontradoException,
    FalhaPersistenciaException, PatrimonioDuplicadoException,
)
from techlab.persistencia import AtivoCsvRepository, ChamadoCsvRepository
from tests.auxiliares import nova_estacao, novo_servidor, novo_switch


class TestAtivoCsv(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self._pasta.name) / "ativos.csv"
        self.repo = AtivoCsvRepository(self.caminho)

    def tearDown(self):
        self._pasta.cleanup()

    def test_arquivo_inexistente_equivale_a_lista_vazia(self):
        self.assertEqual(self.repo.listar(), [])

    def test_crud_e_persistencia_entre_instancias(self):
        self.repo.salvar(novo_servidor())
        self.repo.salvar(nova_estacao())
        self.repo.salvar(novo_switch())
        outra = AtivoCsvRepository(self.caminho)  # simula reiniciar o programa
        self.assertEqual([a.id for a in outra.listar()], [1, 2, 3])
        ativo = outra.buscar_por_id(2)
        ativo.modelo = "Alterado"
        outra.atualizar(ativo)
        self.assertEqual(self.repo.buscar_por_id(2).modelo, "Alterado")
        outra.remover(1)
        self.assertEqual([a.id for a in self.repo.listar()], [2, 3])

    def test_ids_nao_sao_reaproveitados_de_forma_conflitante(self):
        self.repo.salvar(novo_servidor("A"))
        self.repo.salvar(novo_servidor("B"))
        self.repo.remover(1)
        novo = self.repo.salvar(novo_servidor("C"))
        self.assertEqual(novo.id, 3)

    def test_duplicado_e_inexistente(self):
        self.repo.salvar(novo_servidor("X"))
        with self.assertRaises(PatrimonioDuplicadoException):
            self.repo.salvar(novo_servidor("x"))
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.repo.buscar_por_id(50)
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.repo.remover(50)

    def test_arquivo_corrompido(self):
        self.caminho.write_text("id,tipo,codigo_patrimonio,modelo,data_aquisicao,status,detalhes\n"
                                "1,SERVIDOR,A,B,2020-01-01,ATIVO,{json quebrado\n", encoding="utf-8")
        with self.assertRaises(FalhaPersistenciaException):
            self.repo.listar()

    def test_acentos_preservados(self):
        self.repo.salvar(nova_estacao(modelo="Notebook Ação"))
        self.assertEqual(self.repo.listar()[0].modelo, "Notebook Ação")


class TestChamadoCsv(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        pasta = Path(self._pasta.name)
        self.ativos = AtivoCsvRepository(pasta / "ativos.csv")
        self.chamados = ChamadoCsvRepository(pasta / "chamados.csv", self.ativos)
        self.servidor = self.ativos.salvar(novo_servidor())

    def tearDown(self):
        self._pasta.cleanup()

    def test_crud(self):
        c = self.chamados.salvar(ChamadoSuporte("T", "D", "MEDIA", self.servidor))
        self.assertEqual(c.id, 1)
        lido = self.chamados.buscar_por_id(1)
        self.assertEqual(lido.ativo_relacionado.id, self.servidor.id)
        lido.iniciar_atendimento()
        self.chamados.atualizar(lido)
        self.assertEqual(self.chamados.buscar_por_id(1).status.value, "EM_ATENDIMENTO")
        self.chamados.remover(1)
        with self.assertRaises(ChamadoNaoEncontradoException):
            self.chamados.buscar_por_id(1)

    def test_ativo_inexistente(self):
        fantasma = novo_servidor("F")
        fantasma.id = 42
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.chamados.salvar(ChamadoSuporte("T", "D", "BAIXA", fantasma))


if __name__ == "__main__":
    unittest.main()
