# Sistema de Aplicação Incremental de Mudanças de Código

## Visão Geral

O sistema de aplicação incremental permite que mudanças de código descritas em relatórios de implementação sejam aplicadas de forma automática, sequencial e inteligente, com validação e commits atômicos. Ele foi projetado para lidar com grandes volumes de tarefas, paralelizar mudanças independentes e garantir qualidade por meio de testes automatizados.

## Suporte à Exclusão de Arquivos

O sistema agora suporta operações de exclusão de arquivos. Para especificar uma exclusão, inclua uma entrada com `status: 'DELETE'` no campo `conjunto_de_mudancas` do payload ou relatório de implementação. O pipeline de commits processa essas exclusões para GitHub, GitLab e Azure DevOps.

Exemplo de JSON:

{
  "grupos": [
    {
      "titulo_pr": "Remover módulos obsoletos",
      "branch_sugerida": "cleanup/remove-deprecated",
      "resumo_do_pr": "Remove arquivos deprecados que não são mais utilizados.",
      "conjunto_de_mudancas": [
        {
          "caminho_do_arquivo": "backend/app/deprecated_module.py",
          "status": "DELETE",
          "conteudo": null,
          "justificativa": "Módulo obsoleto removido após migração para nova arquitetura."
        }
      ]
    }
  ]
}

A operação é idempotente: se o arquivo já foi excluído, o sistema não falha. Rollback de exclusão recria o arquivo com o conteúdo original armazenado no cache de contexto.

## Arquitetura

- **Parser de Relatório:** Extrai tarefas de código do relatório markdown, incluindo exclusões.
- **Analisador de Dependências:** Constrói grafo de dependências entre tarefas.
- **Cache de Contexto:** Otimiza leituras de arquivos do repositório.
- **Executor de Mudança:** Aplica cada tarefa individualmente via LLM, incluindo exclusão.
- **Validador de Mudança:** Executa testes automatizados após cada mudança.
- **Committer Incremental:** Cria commits atômicos por tarefa ou grupo de tarefas, incluindo exclusões.
- **Orquestrador:** Gerencia execução sequencial/paralela e checkpoints.

## Fluxo de Execução

1. Relatório de implementação é gerado.
2. Parser extrai tarefas de código e exclusão.
3. Analisador constrói grafo de dependências e sugere ordem ótima de execução.
4. Orquestrador executa tarefas em ordem, paralelizando grupos independentes.
5. Executor aplica cada mudança via LLM com contexto reduzido, incluindo exclusão.
6. Mudança é validada por testes automatizados.
7. Commit incremental é criado, incluindo exclusão.
8. Checkpoints são salvos para retomada em caso de falha.
9. Workflow segue para aprovação e PR.

## Como Usar

- Ative o modo incremental enviando `aplicar_mudancas_incrementalmente=true` no payload da API `/start-analysis`.
- Para excluir arquivos, inclua `status: 'DELETE'` e o caminho do arquivo no plano de implementação.

## Flags e Estratégias

- `pause_on_high_impact`: Pausa execução antes de tarefas que podem impactar muitos arquivos.
- `commit_strategy`: Permite escolher granularidade dos commits (`per_task`, `per_layer`, `single`).

## Considerações Técnicas

- Exclusão é idempotente e não falha se o arquivo já foi removido.
- Rollback recria o arquivo excluído com o conteúdo original.
- Validação de dependências impede exclusão de arquivos críticos sem aprovação.
- Logs detalhados são gerados para cada exclusão.
