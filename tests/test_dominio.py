import unittest
from datetime import date, timedelta

from techlab.dominio import (
    AtivoTI, ChamadoSuporte, Prioridade, StatusAtivo, StatusChamado, criar_ativo,
)
from techlab.excecoes import DadosInvalidosException, OperacaoNaoPermitidaException
from tests.auxiliares import nova_estacao, novo_servidor, novo_switch


class TestAtivoTI(unittest.TestCase):
    def test_classe_base_e_abstrata(self):
        with self.assertRaises(TypeError):
            AtivoTI("A", "B", "2020-01-01")

    def test_codigo_normalizado_em_maiusculas(self):
        self.assertEqual(novo_servidor(codigo=" srv-9 ").codigo_patrimonio, "SRV-9")

    def test_campos_obrigatorios(self):
        with self.assertRaises(DadosInvalidosException):
            novo_servidor(codigo="  ")
        with self.assertRaises(DadosInvalidosException):
            novo_servidor(modelo="")

    def test_data_futura_rejeitada(self):
        futuro = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(DadosInvalidosException):
            novo_servidor(data=futuro)

    def test_data_invalida_rejeitada(self):
        with self.assertRaises(DadosInvalidosException):
            novo_servidor(data="31/02/2020")

    def test_status_aceita_texto_e_rejeita_invalido(self):
        s = novo_servidor()
        s.status = "em manutenção"
        self.assertEqual(s.status, StatusAtivo.EM_MANUTENCAO)
        with self.assertRaises(DadosInvalidosException):
            s.status = "quebrado"

    def test_ip_invalido(self):
        with self.assertRaises(DadosInvalidosException):
            criar_ativo("SERVIDOR", "X", "Y", "2020-01-01", ip="999.1.1.1",
                        sistema_operacional="L", memoria_gb=8, num_cpus=2)

    def test_polimorfismo_vida_util(self):
        self.assertEqual(
            [novo_servidor().vida_util_anos(), nova_estacao().vida_util_anos(), novo_switch().vida_util_anos()],
            [5, 4, 7],
        )

    def test_precisa_renovacao(self):
        s = novo_servidor(data="2020-01-10")
        self.assertTrue(s.precisa_renovacao(date(2025, 1, 10)))
        self.assertFalse(s.precisa_renovacao(date(2025, 1, 9)))

    def test_fabrica_tipo_desconhecido_e_atributos_errados(self):
        with self.assertRaises(DadosInvalidosException):
            criar_ativo("IMPRESSORA", "A", "B", "2020-01-01")
        with self.assertRaises(DadosInvalidosException):
            criar_ativo("SERVIDOR", "A", "B", "2020-01-01", cor="azul")

    def test_ida_e_volta_para_dict(self):
        from techlab.dominio import ativo_de_dict
        original = nova_estacao()
        copia = ativo_de_dict(original.para_dict())
        self.assertEqual(copia.para_dict(), original.para_dict())
        self.assertIsInstance(copia, type(original))


class TestChamado(unittest.TestCase):
    def test_ciclo_de_vida(self):
        c = ChamadoSuporte("Título", "Descrição", "alta", novo_servidor())
        self.assertEqual(c.prioridade, Prioridade.ALTA)
        self.assertEqual(c.status, StatusChamado.ABERTO)
        c.iniciar_atendimento()
        c.fechar()
        self.assertFalse(c.aberto)
        with self.assertRaises(OperacaoNaoPermitidaException):
            c.fechar()

    def test_exige_ativo_valido(self):
        with self.assertRaises(DadosInvalidosException):
            ChamadoSuporte("T", "D", "BAIXA", "não é ativo")

    def test_prioridade_invalida(self):
        with self.assertRaises(DadosInvalidosException):
            ChamadoSuporte("T", "D", "urgentíssima", novo_servidor())

    def test_prioridade_por_numero_e_sem_acento(self):
        self.assertEqual(Prioridade.de_valor(4), Prioridade.CRITICA)
        self.assertEqual(Prioridade.de_valor("média"), Prioridade.MEDIA)


if __name__ == "__main__":
    unittest.main()
