import unittest

from techlab.dominio import ChamadoSuporte, StatusAtivo
from techlab.excecoes import (
    ChamadoNaoEncontradoException, DadosInvalidosException,
    EquipamentoNaoEncontradoException, FalhaConexaoBDException,
    OperacaoNaoPermitidaException, PatrimonioDuplicadoException,
)
from techlab.persistencia import AtivoRepository, ChamadoRepository, ConexaoSQLite, criar_schema
from tests.auxiliares import nova_estacao, novo_servidor, novo_switch


class BaseSQLite(unittest.TestCase):
    def setUp(self):
        self.conexao = ConexaoSQLite(":memory:")
        self.conexao.conectar()
        criar_schema(self.conexao)
        self.ativos = AtivoRepository(self.conexao)
        self.chamados = ChamadoRepository(self.conexao, self.ativos)

    def tearDown(self):
        self.conexao.desconectar()


class TestConexao(unittest.TestCase):
    def test_usar_sem_conectar_lanca_excecao(self):
        with self.assertRaises(FalhaConexaoBDException):
            ConexaoSQLite(":memory:").obter_conexao()

    def test_caminho_impossivel_lanca_excecao(self):
        with self.assertRaises(FalhaConexaoBDException):
            ConexaoSQLite("/proc/nao/existe/techlab.db").conectar()


class TestAtivoRepository(BaseSQLite):
    def test_crud_completo(self):
        ativo = self.ativos.salvar(novo_servidor())
        self.assertEqual(ativo.id, 1)
        lido = self.ativos.buscar_por_id(1)
        self.assertEqual(lido.para_dict(), ativo.para_dict())
        lido.modelo = "Novo modelo"
        lido.status = StatusAtivo.INATIVO
        self.ativos.atualizar(lido)
        self.assertEqual(self.ativos.buscar_por_id(1).modelo, "Novo modelo")
        self.ativos.remover(1)
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.ativos.buscar_por_id(1)

    def test_polimorfismo_na_leitura(self):
        for ativo in (novo_servidor(), nova_estacao(), novo_switch()):
            self.ativos.salvar(ativo)
        tipos = [type(a).__name__ for a in self.ativos.listar()]
        self.assertEqual(tipos, ["Servidor", "EstacaoTrabalho", "DispositivoRede"])

    def test_patrimonio_duplicado(self):
        self.ativos.salvar(novo_servidor("SRV-1"))
        with self.assertRaises(PatrimonioDuplicadoException):
            self.ativos.salvar(novo_servidor("srv-1"))

    def test_atualizar_e_remover_inexistente(self):
        fantasma = novo_servidor()
        fantasma.id = 99
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.ativos.atualizar(fantasma)
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.ativos.remover(99)

    def test_atualizar_sem_id(self):
        with self.assertRaises(DadosInvalidosException):
            self.ativos.atualizar(novo_servidor())

    def test_ordenacao_com_lista_de_permissao(self):
        self.ativos.salvar(novo_servidor("B-2"))
        self.ativos.salvar(novo_servidor("A-1"))
        codigos = [a.codigo_patrimonio for a in self.ativos.listar("codigo_patrimonio")]
        self.assertEqual(codigos, ["A-1", "B-2"])
        with self.assertRaises(DadosInvalidosException):
            self.ativos.listar("id; DROP TABLE ativos")

    def test_sql_injection_em_busca(self):
        self.ativos.salvar(novo_servidor())
        ataques = ["'; DROP TABLE ativos; --", "' OR '1'='1", "%", "_"]
        for ataque in ataques:
            self.assertEqual(self.ativos.buscar_por_modelo(ataque), [], ataque)
        self.assertEqual(len(self.ativos.listar()), 1)  # tabela continua intacta

    def test_sql_injection_em_id(self):
        self.ativos.salvar(novo_servidor())
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.ativos.buscar_por_id("1 OR 1=1")
        self.assertEqual(len(self.ativos.listar()), 1)

    def test_sql_injection_em_dados_gravados(self):
        ativo = novo_servidor(modelo="x'); DROP TABLE ativos; --")
        self.ativos.salvar(ativo)
        self.assertEqual(self.ativos.buscar_por_id(ativo.id).modelo, "x'); DROP TABLE ativos; --")


class TestChamadoRepository(BaseSQLite):
    def setUp(self):
        super().setUp()
        self.servidor = self.ativos.salvar(novo_servidor())

    def test_crud(self):
        c = self.chamados.salvar(ChamadoSuporte("Lento", "Muito lento", "ALTA", self.servidor))
        self.assertEqual(c.id, 1)
        lido = self.chamados.buscar_por_id(1)
        self.assertEqual(lido.ativo_relacionado.codigo_patrimonio, "SRV-01")
        lido.fechar()
        self.chamados.atualizar(lido)
        self.assertFalse(self.chamados.buscar_por_id(1).aberto)
        self.chamados.remover(1)
        with self.assertRaises(ChamadoNaoEncontradoException):
            self.chamados.buscar_por_id(1)

    def test_ativo_com_chamado_nao_pode_ser_removido(self):
        self.chamados.salvar(ChamadoSuporte("T", "D", "BAIXA", self.servidor))
        with self.assertRaises(OperacaoNaoPermitidaException):
            self.ativos.remover(self.servidor.id)

    def test_chamado_para_ativo_inexistente(self):
        fantasma = novo_servidor("FANTASMA")
        fantasma.id = 77
        with self.assertRaises(EquipamentoNaoEncontradoException):
            self.chamados.salvar(ChamadoSuporte("T", "D", "BAIXA", fantasma))

    def test_chamado_sem_ativo_persistido(self):
        with self.assertRaises(DadosInvalidosException):
            self.chamados.salvar(ChamadoSuporte("T", "D", "BAIXA", novo_servidor("NOVO")))


if __name__ == "__main__":
    unittest.main()
