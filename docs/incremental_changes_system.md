# Sistema de Aplicação Incremental de Mudanças de Código

## Visão Geral

O sistema de aplicação incremental permite que mudanças de código descritas em relatórios de implementação sejam aplicadas de forma automática, sequencial e inteligente, com validação e commits atômicos. Ele foi projetado para lidar com grandes volumes de tarefas, paralelizar mudanças independentes e garantir qualidade por meio de testes automatizados.

## Arquitetura

- **Parser de Relatório:** Extrai tarefas de código do relatório markdown.
- **Analisador de Dependências:** Constrói grafo de dependências entre tarefas.
- **Cache de Contexto:** Otimiza leituras de arquivos do repositório.
- **Executor de Mudança:** Aplica cada tarefa individualmente via LLM.
- **Validador de Mudança:** Executa testes unitários e de integração após cada mudança.
- **Committer Incremental:** Cria commits atômicos por tarefa ou grupo de tarefas.
- **Orquestrador:** Gerencia execução sequencial/paralela e checkpoints.

## Fluxo de Execução

1. Relatório de implementação é gerado.
2. Parser extrai tarefas de código.
3. Analisador constrói grafo de dependências e sugere ordem ótima de execução.
4. Orquestrador executa tarefas em ordem, paralelizando grupos independentes.
5. Executor aplica cada mudança via LLM com contexto reduzido.
6. Mudança é validada por testes automatizados.
7. Commit incremental é criado.
8. Checkpoints são salvos para retomada em caso de falha.
9. Workflow segue para aprovação e PR.

## Como Usar

- Ative o modo incremental enviando `aplicar_mudancas_incrementalmente=true` no payload da API `/start-analysis`.
- O relatório de implementação deve seguir formato de tabela markdown com colunas: Passo, Camada, Ação, Caminho do Arquivo, Descrição.
- Apenas tarefas de código são processadas; tarefas de infraestrutura devem ser executadas manualmente.
- É recomendado que o repositório tenha testes unitários e de integração configurados.

## Flags e Estratégias

- `pause_on_high_impact`: Pausa execução antes de tarefas que podem impactar muitos arquivos.
- `commit_strategy`: Permite escolher granularidade dos commits (`per_task`, `per_layer`, `single`).

## Otimizações e Configurações Avançadas

### Flag `pause_on_high_impact`
Permite que o sistema pause a execução incremental antes de aplicar tarefas que podem impactar um número elevado de arquivos (por exemplo, mais de 10). Quando ativada, o workflow aguarda aprovação manual antes de prosseguir com estas tarefas, reduzindo riscos de grandes regressões. O sistema loga as tarefas de alto impacto e recomenda revisão manual.

### Flag `commit_strategy`
Permite escolher a granularidade dos commits incrementais:
- `per_task`: Um commit para cada tarefa individual.
- `per_layer`: Um commit agrupado para todas as tarefas de uma mesma camada (ex: "Domínio", "Serviços").
- `single`: Um único commit para todas as tarefas do relatório.
A estratégia utilizada é logada para auditoria e pode ser definida no payload da API.

### Métricas de Performance
- **Cache hit rate:** O sistema calcula e loga a taxa de acertos do cache de contexto, indicando a eficiência do cache em evitar leituras repetidas do repositório. Exemplo de log: `Cache hit rate: 85.3%`.
- **Tempo de execução por tarefa:** Cada tarefa tem seu tempo de execução logado, permitindo análise de gargalos e otimização futura.
- **Paralelização efetiva:** O sistema loga quantas tarefas foram executadas em paralelo em cada nível do grafo de dependências.

### Interpretação de Logs de Execução Incremental
- Logs detalham ordem de execução sugerida, tarefas de alto impacto, checkpoints salvos, resultados de testes, commits realizados e eventuais falhas.
- Logs de paralelização indicam grupos independentes de tarefas executados simultaneamente.
- Logs de rollback detalham reversões de commits em caso de falha de validação.

### Troubleshooting de Problemas Comuns
- **Tarefa falha por timeout:** O sistema tenta até 3 vezes com backoff exponencial. Se todas falharem, tarefa é marcada como failed e dependentes são puladas.
- **Como aumentar timeout:** Ajuste o parâmetro de timeout no serviço de execução de tarefas ou na configuração do LLM provider.
- **Parsing do relatório falha:** Verifique se o relatório segue o formato de tabela markdown com as colunas obrigatórias. Consulte exemplos válidos abaixo.
- **Testes de integração não são encontrados:** Certifique-se que arquivos de teste de integração seguem o padrão `test_integration_*.py` e importam os arquivos modificados.
- **Execução incremental é lenta:** Verifique logs de cache hit rate e paralelização. Considere aumentar número de threads se o rate limiting do LLM permitir.

## Exemplos de Relatórios

Relatório válido:

| Passo # | Camada | Ação | Caminho do Arquivo | Descrição |
|---|---|---|---|---|
| 1 | Domínio | CRIAR | `domain/models/rbac_models.py` | Criar modelo RBAC |
| 2 | Serviços | MODIFICAR | `services/rbac_service.py` | Adicionar lógica de autorização |

Relatório inválido:

- Tabela sem colunas obrigatórias
- Passos de infraestrutura misturados com tarefas de código

## Referências

- [README principal](../README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [networkx Documentation](https://networkx.org/)
