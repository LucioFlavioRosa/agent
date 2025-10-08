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

## Otimizações

- Cache de contexto reduz leituras repetidas de arquivos.
- Paralelização de tarefas independentes (até 3 simultâneas).
- Checkpoints permitem retomada após falha.
- Sugestão de ordem ótima prioriza tarefas críticas e complexas.

## Limitações

- Sistema depende de relatórios bem estruturados.
- Mudanças de infraestrutura não são aplicadas automaticamente.
- Detecção de dependências implícitas pode ser limitada.

## Troubleshooting

- Se parsing do relatório falhar, valide formato conforme exemplos abaixo.
- Se tarefas de alto impacto forem detectadas, revise manualmente antes de continuar.
- Em caso de falha, use o endpoint `/resume-incremental-changes/{job_id}` para retomar execução.

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
