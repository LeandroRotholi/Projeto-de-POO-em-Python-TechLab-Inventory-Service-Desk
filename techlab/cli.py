"""Interface de linha de comando (camada de apresentação)."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Any, Callable, Optional

from techlab.aplicacao import BACKENDS, Aplicacao, construir_aplicacao
from techlab.dados_demo import popular_demo
from techlab.dominio import StatusAtivo, tipos_disponiveis
from techlab.dominio.ativo_ti import AtivoTI
from techlab.dominio.chamado_suporte import ChamadoSuporte, Prioridade
from techlab.excecoes import DadosInvalidosException, TechLabError
from techlab.notificacao import NotificadorArquivo, NotificadorConsole
from techlab.persistencia import AtivoCsvRepository

# campo, rótulo, conversor
CAMPOS_POR_TIPO: dict[str, list[tuple[str, str, Callable[[str], Any]]]] = {
    "SERVIDOR": [
        ("ip", "Endereço IP", str),
        ("sistema_operacional", "Sistema operacional", str),
        ("memoria_gb", "Memória (GB)", int),
        ("num_cpus", "Número de CPUs", int),
    ],
    "ESTACAO_TRABALHO": [
        ("usuario_responsavel", "Usuário responsável", str),
        ("setor", "Setor", str),
        ("sistema_operacional", "Sistema operacional", str),
    ],
    "DISPOSITIVO_REDE": [
        ("tipo_dispositivo", "Tipo (switch, roteador, access point...)", str),
        ("endereco_ip", "Endereço IP", str),
        ("numero_portas", "Número de portas", int),
    ],
}


# ----------------------------- entrada de dados -----------------------------
def ler_texto(rotulo: str, obrigatorio: bool = True) -> str:
    while True:
        valor = input(f"{rotulo}: ").strip()
        if valor or not obrigatorio:
            return valor
        print("  Campo obrigatório.")


def ler_inteiro(rotulo: str) -> int:
    try:
        return int(ler_texto(rotulo))
    except ValueError:
        raise DadosInvalidosException("Informe um número inteiro.")


def ler_data(rotulo: str) -> str:
    texto = ler_texto(f"{rotulo} (AAAA-MM-DD ou DD/MM/AAAA)")
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise DadosInvalidosException("Data inválida.")


def escolher(rotulo: str, opcoes: list[str]) -> str:
    print(rotulo)
    for numero, opcao in enumerate(opcoes, start=1):
        print(f"  {numero}) {opcao}")
    escolha = ler_inteiro("Opção")
    if not 1 <= escolha <= len(opcoes):
        raise DadosInvalidosException("Opção fora da lista.")
    return opcoes[escolha - 1]


# ------------------------------- saída formatada -------------------------------
def imprimir_ativos(ativos: list[AtivoTI]) -> None:
    if not ativos:
        print("  (nenhum equipamento encontrado)")
        return
    print(f"  {'ID':>3}  {'PATRIMÔNIO':<10} {'TIPO':<17} {'MODELO':<26} {'STATUS':<14} AQUISIÇÃO")
    for a in ativos:
        print(
            f"  {a.id:>3}  {a.codigo_patrimonio:<10} {a.tipo:<17} {a.modelo[:26]:<26} "
            f"{a.status.value:<14} {a.data_aquisicao.isoformat()}"
        )


def imprimir_chamados(chamados: list[ChamadoSuporte]) -> None:
    if not chamados:
        print("  (nenhum chamado encontrado)")
        return
    for c in chamados:
        print(f"  {c}")


# --------------------------------- ações do menu ---------------------------------
def acao_cadastrar(app: Aplicacao) -> None:
    tipo = escolher("Tipo de equipamento:", tipos_disponiveis())
    codigo = ler_texto("Código de patrimônio")
    modelo = ler_texto("Modelo")
    data = ler_data("Data de aquisição")
    detalhes: dict[str, Any] = {}
    for campo, rotulo, conversor in CAMPOS_POR_TIPO[tipo]:
        bruto = ler_texto(rotulo)
        try:
            detalhes[campo] = conversor(bruto)
        except ValueError:
            raise DadosInvalidosException(f"Valor inválido para '{rotulo}'.")
    app.inventario.cadastrar_novo(tipo, codigo, modelo, data, **detalhes)


def acao_listar(app: Aplicacao) -> None:
    imprimir_ativos(app.inventario.listar())


def acao_buscar(app: Aplicacao) -> None:
    ativo = app.inventario.buscar_por_codigo(ler_texto("Código de patrimônio"))
    print(f"  {ativo.descricao_detalhada()}")
    chamados = app.service_desk.chamados_do_ativo(ativo.id)
    print(f"  Chamados vinculados: {len(chamados)}")
    imprimir_chamados(chamados)


def acao_filtrar(app: Aplicacao) -> None:
    print("Deixe em branco para ignorar um filtro.")
    tipo = ler_texto(f"Tipo ({', '.join(tipos_disponiveis())})", obrigatorio=False)
    status = ler_texto(f"Status ({', '.join(s.value for s in StatusAtivo)})", obrigatorio=False)
    termo = ler_texto("Trecho do modelo", obrigatorio=False)
    chave = ler_texto(
        "Ordenar por (id, codigo_patrimonio, modelo, data_aquisicao, status, tipo)",
        obrigatorio=False,
    ) or "codigo_patrimonio"
    decrescente = ler_texto("Ordem decrescente? (s/N)", obrigatorio=False).lower() == "s"
    filtrados = app.inventario.filtrar(tipo or None, status or None, termo or None)
    imprimir_ativos(app.inventario.ordenar(filtrados, chave, decrescente))


def acao_alterar_status(app: Aplicacao) -> None:
    id_ativo = ler_inteiro("ID do equipamento")
    novo = escolher("Novo status:", [s.value for s in StatusAtivo])
    app.inventario.alterar_status(id_ativo, novo)


def acao_remover(app: Aplicacao) -> None:
    id_ativo = ler_inteiro("ID do equipamento")
    ativo = app.inventario.obter(id_ativo)
    if ler_texto(f"Remover {ativo.codigo_patrimonio}? (s/N)", obrigatorio=False).lower() == "s":
        app.inventario.remover(id_ativo)
    else:
        print("  Operação cancelada.")


def acao_abrir_chamado(app: Aplicacao) -> None:
    id_ativo = ler_inteiro("ID do equipamento")
    titulo = ler_texto("Título")
    descricao = ler_texto("Descrição")
    prioridade = escolher("Prioridade:", [p.name for p in Prioridade])
    app.service_desk.abrir_chamado(titulo, descricao, prioridade, id_ativo)


def acao_listar_chamados(app: Aplicacao) -> None:
    status = ler_texto("Filtrar por status (ABERTO, EM_ATENDIMENTO, FECHADO)", obrigatorio=False)
    imprimir_chamados(app.service_desk.listar(status or None))


def acao_atender_chamado(app: Aplicacao) -> None:
    id_chamado = ler_inteiro("ID do chamado")
    acao = escolher("Ação:", ["Iniciar atendimento", "Fechar chamado"])
    if acao.startswith("Iniciar"):
        app.service_desk.iniciar_atendimento(id_chamado)
    else:
        app.service_desk.fechar_chamado(id_chamado)


def acao_relatorios(app: Aplicacao) -> None:
    print("  Equipamentos por status:")
    for status, qtd in sorted(app.inventario.contar_por_status().items()):
        print(f"    {status:<14} {qtd}")
    print("  Equipamentos por tipo:")
    for tipo, lista in sorted(app.inventario.agrupar_por_tipo().items()):
        print(f"    {tipo:<17} {len(lista)}")
    print("  Chamados abertos por prioridade:")
    for prioridade, qtd in app.service_desk.contar_por_prioridade().items():
        print(f"    {prioridade:<8} {qtd}")
    print("  Equipamentos que atingiram a vida útil recomendada:")
    imprimir_ativos(app.inventario.ativos_para_renovacao())


def acao_exportar(app: Aplicacao) -> None:
    caminho = ler_texto("Arquivo CSV de destino", obrigatorio=False) or "dados/exportacao.csv"
    novos, ignorados = app.inventario.exportar_para(AtivoCsvRepository(caminho))
    print(f"  Exportados: {novos}. Ignorados (já existiam): {ignorados}. Arquivo: {caminho}")


def acao_importar(app: Aplicacao) -> None:
    caminho = ler_texto("Arquivo CSV de origem", obrigatorio=False) or "dados/ativos.csv"
    app.inventario.importar_de(AtivoCsvRepository(caminho))


MENU: list[tuple[str, str, Callable[[Aplicacao], None]]] = [
    ("1", "Cadastrar equipamento", acao_cadastrar),
    ("2", "Listar equipamentos", acao_listar),
    ("3", "Buscar equipamento por patrimônio", acao_buscar),
    ("4", "Filtrar e ordenar equipamentos", acao_filtrar),
    ("5", "Alterar status de equipamento", acao_alterar_status),
    ("6", "Remover equipamento", acao_remover),
    ("7", "Abrir chamado de suporte", acao_abrir_chamado),
    ("8", "Listar chamados", acao_listar_chamados),
    ("9", "Atender / fechar chamado", acao_atender_chamado),
    ("10", "Relatórios", acao_relatorios),
    ("11", "Exportar equipamentos para CSV", acao_exportar),
    ("12", "Importar equipamentos de CSV", acao_importar),
]


def executar_menu(app: Aplicacao) -> None:
    acoes = {codigo: funcao for codigo, _, funcao in MENU}
    while True:
        print(f"\n=== TechLab Inventory & Service Desk  [{app.backend}] ===")
        for codigo, titulo, _ in MENU:
            print(f"  {codigo:>2}) {titulo}")
        print("   0) Sair")
        try:
            opcao = input("Escolha: ").strip()
        except EOFError:
            print()
            return
        if opcao == "0":
            return
        funcao = acoes.get(opcao)
        if funcao is None:
            print("  Opção inválida.")
            continue
        try:
            funcao(app)
        except TechLabError as erro:
            print(f"  ERRO: {erro}")
        except EOFError:
            print()
            return


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="techlab", description="TechLab Inventory & Service Desk"
    )
    parser.add_argument("--backend", choices=BACKENDS, default="sqlite",
                        help="onde os dados são gravados (padrão: sqlite)")
    parser.add_argument("--dados", default="dados", help="pasta dos arquivos de dados")
    parser.add_argument("--demo", action="store_true",
                        help="carrega dados de exemplo se o inventário estiver vazio")
    parser.add_argument("--log", metavar="ARQUIVO",
                        help="grava as notificações em arquivo em vez de exibir no terminal")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    argumentos = criar_parser().parse_args(argv)
    notificador = NotificadorArquivo(argumentos.log) if argumentos.log else NotificadorConsole()
    try:
        app = construir_aplicacao(argumentos.backend, argumentos.dados, notificador)
    except TechLabError as erro:
        print(f"Não foi possível iniciar o sistema: {erro}", file=sys.stderr)
        return 1
    try:
        if argumentos.demo and not app.inventario.listar():
            popular_demo(app.inventario, app.service_desk)
            print("Dados de demonstração carregados.")
        executar_menu(app)
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
    finally:
        app.encerrar()
    return 0
