"""Dados de exemplo para demonstrar o sistema."""

from __future__ import annotations

from techlab.servicos import InventarioService, ServiceDesk


def popular_demo(inventario: InventarioService, service_desk: ServiceDesk) -> None:
    srv = inventario.cadastrar_novo(
        "SERVIDOR", "SRV-001", "Dell PowerEdge R740", "2019-05-20",
        ip="10.0.0.10", sistema_operacional="Ubuntu Server 22.04", memoria_gb=128, num_cpus=24,
    )
    inventario.cadastrar_novo(
        "SERVIDOR", "SRV-002", "HPE ProLiant DL380", "2023-02-14",
        ip="10.0.0.11", sistema_operacional="Debian 12", memoria_gb=64, num_cpus=16,
    )
    est = inventario.cadastrar_novo(
        "ESTACAO_TRABALHO", "EST-101", "Lenovo ThinkCentre M70", "2022-08-01",
        usuario_responsavel="Ana Souza", setor="Financeiro", sistema_operacional="Windows 11",
    )
    inventario.cadastrar_novo(
        "ESTACAO_TRABALHO", "EST-102", "Dell OptiPlex 3080", "2020-01-15",
        usuario_responsavel="Carlos Lima", setor="RH", sistema_operacional="Windows 10",
    )
    rede = inventario.cadastrar_novo(
        "DISPOSITIVO_REDE", "NET-201", "Cisco Catalyst 2960", "2018-11-30",
        tipo_dispositivo="switch", endereco_ip="10.0.1.1", numero_portas=48,
    )
    service_desk.abrir_chamado(
        "Servidor lento no horário de pico", "CPU em 95% entre 14h e 16h.", "ALTA", srv.id
    )
    service_desk.abrir_chamado(
        "Monitor sem sinal", "Usuária relata tela preta ao iniciar.", "BAIXA", est.id
    )
    service_desk.abrir_chamado(
        "Switch sem comunicação com o andar 2", "Perda total de link nas portas 1 a 24.", "CRITICA", rede.id
    )
