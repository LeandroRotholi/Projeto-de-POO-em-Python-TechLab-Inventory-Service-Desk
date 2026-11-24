# Arquitetura do TechLab

## Princípios

1. **Camadas com dependência em uma só direção.** A interface (CLI) chama serviços, que chamam
   contratos (interfaces), implementados pela infraestrutura. O domínio não conhece ninguém.
2. **Programar para interfaces, não para implementações.** `InventarioService` recebe um
   `IPersistencia[AtivoTI]`; não sabe se por trás há CSV ou SQLite.
3. **Composição na borda.** Somente `aplicacao.py` instancia classes concretas
   (injeção de dependências manual).
4. **Falhar com exceções específicas.** Todas herdam de `TechLabError`; a CLI captura
   e mostra mensagens amigáveis.

## Decisões de projeto

| Decisão | Motivo |
|---|---|
| Tabela única `ativos` com coluna `tipo` e `detalhes` em JSON | Evita uma tabela por subclasse e mantém o CRUD simples; novas subclasses não exigem alterar o schema. Em contrapartida, os atributos específicos não são consultáveis por SQL puro. |
| Cada repositório devolve a subclasse correta (`ativo_de_dict`) | O restante do sistema usa polimorfismo (`vida_util_anos`, `descricao_detalhada`) sem `if tipo == ...`. |
| Gravação atômica no CSV (arquivo temporário + `os.replace`) | Impede arquivo pela metade em caso de falha. |
| `ON DELETE RESTRICT` na chave estrangeira | Um equipamento com chamados não pode ser apagado e deixar chamados órfãos. |
| Regra: chamado CRITICA coloca o ativo em `EM_MANUTENCAO` | Demonstra colaboração entre `ServiceDesk` e `InventarioService`. O ativo volta a `ATIVO` ao fechar o último chamado aberto. |

## Proteção contra SQL Injection

- Valores do usuário **nunca** são concatenados em SQL: usam-se parâmetros `?`.
- O único trecho dinâmico (`ORDER BY`) valida a coluna contra `COLUNAS_ORDENAVEIS`.
- `LIKE` escapa `%`, `_` e `\` do termo buscado.
- Os testes `test_sql_injection_*` tentam ataques clássicos e verificam que a tabela permanece intacta.

## Limitação conhecida

No backend CSV não há chave estrangeira; por isso o banco relacional é a etapa que garante a
integridade entre chamados e equipamentos.
