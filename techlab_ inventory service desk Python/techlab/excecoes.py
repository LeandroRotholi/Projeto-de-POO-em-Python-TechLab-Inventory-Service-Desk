"""Exceções personalizadas do TechLab.

Todas herdam de TechLabError, o que permite capturar qualquer falha
do sistema com um único ``except TechLabError``.
"""


class TechLabError(Exception):
    """Classe base de todas as exceções do sistema."""


class DadosInvalidosException(TechLabError):
    """Algum dado informado não passou na validação."""


class OperacaoNaoPermitidaException(TechLabError):
    """A operação viola uma regra de negócio ou de integridade."""


class EquipamentoNaoEncontradoException(TechLabError):
    """Nenhum ativo de TI foi encontrado para o identificador informado."""

    def __init__(self, identificador):
        self.identificador = identificador
        super().__init__(f"Equipamento não encontrado: {identificador}")


class ChamadoNaoEncontradoException(TechLabError):
    """Nenhum chamado foi encontrado para o identificador informado."""

    def __init__(self, identificador):
        self.identificador = identificador
        super().__init__(f"Chamado não encontrado: {identificador}")


class PatrimonioDuplicadoException(TechLabError):
    """Já existe um ativo cadastrado com o mesmo código de patrimônio."""

    def __init__(self, codigo):
        self.codigo = codigo
        super().__init__(f"Já existe um equipamento com o patrimônio '{codigo}'.")


class FalhaConexaoBDException(TechLabError):
    """Não foi possível abrir ou usar a conexão com o banco de dados."""


class FalhaPersistenciaException(TechLabError):
    """Erro ao ler ou gravar dados (arquivo ou banco)."""
