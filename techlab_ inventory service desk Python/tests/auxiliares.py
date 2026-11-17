"""Fábricas de objetos usadas pelos testes."""

from techlab.dominio import criar_ativo


def novo_servidor(codigo="SRV-01", modelo="Dell R740", data="2020-01-10"):
    return criar_ativo(
        "SERVIDOR", codigo, modelo, data,
        ip="10.0.0.5", sistema_operacional="Ubuntu", memoria_gb=64, num_cpus=16,
    )


def nova_estacao(codigo="EST-01", modelo="Lenovo M70", data="2023-03-01"):
    return criar_ativo(
        "ESTACAO_TRABALHO", codigo, modelo, data,
        usuario_responsavel="Ana", setor="Financeiro", sistema_operacional="Windows 11",
    )


def novo_switch(codigo="NET-01", modelo="Cisco 2960", data="2017-06-01"):
    return criar_ativo(
        "DISPOSITIVO_REDE", codigo, modelo, data,
        tipo_dispositivo="Switch", endereco_ip="10.0.1.1", numero_portas=24,
    )
