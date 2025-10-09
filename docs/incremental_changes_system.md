# Sistema de Aplicação Incremental de Mudanças de Código

## Visão Geral

O sistema de aplicação incremental permite que mudanças de código descritas em relatórios de implementação sejam aplicadas de forma automática, sequencial e inteligente, com validação e commits atômicos. Ele foi projetado para lidar com grandes volumes de tarefas, paralelizar mudanças independentes e garantir qualidade por meio de testes automatizados.

## Suporte à Exclusão de Arquivos

Agora é possível especificar exclusões de arquivos no plano de implementação. Para excluir um arquivo, adicione uma entrada no conjunto_de_mudancas com:


{
  "caminho_do_arquivo": "backend/app/deprecated_module.py",
  "status": "DELETE",
  "conteudo": null,
  "justificativa": "Módulo obsoleto removido após migração para nova arquitetura."
}


O sistema irá processar a exclusão em todos os provedores suportados (GitHub, GitLab, Azure DevOps). No modo incremental, a exclusão é registrada em deleted_files no resultado da tarefa.

## Arquitetura

- **Parser de Relatório:** Extrai tarefas de código do relatório markdown, incluindo exclusões.
- **Analisador de Dependências:** Constrói grafo de dependências entre tarefas.
- **Cache de Contexto:** Otimiza leituras de arquivos do repositório.
- **Executor de Mudança:** Aplica cada tarefa individualmente via LLM, incluindo exclusões.
- **Validador de Mudança:** Executa testes unitários e de integração após cada mudança.
- **Committer Incremental:** Cria commits atômicos por tarefa ou grupo de tarefas, incluindo exclusões.
- **Orquestrador:** Gerencia execução sequencial/paralela e checkpoints.

## Fluxo de Execução

1. Relatório de implementação é gerado.
2. Parser extrai tarefas de código, incluindo exclusões.
3. Analisador constrói grafo de dependências e sugere ordem ótima de execução.
4. Orquestrador executa tarefas em ordem, paralelizando grupos independentes.
5. Executor aplica cada mudança via LLM com contexto reduzido, processando exclusões quando necessário.
6. Mudança é validada por testes automatizados.
7. Commit incremental é criado, incluindo exclusões.
8. Checkpoints são salvos para retomada em caso de falha.
9. Workflow segue para aprovação e PR.

## Como Usar

- Para excluir um arquivo, inclua uma entrada com `status: 'DELETE'` no conjunto_de_mudancas do payload.
- No modo incremental, a exclusão será refletida no campo deleted_files do resultado da tarefa.

## Exemplos de Relatórios

Relatório com exclusão:

| Passo # | Camada | Ação | Caminho do Arquivo | Descrição |
|---|---|---|---|---|
| 3 | Serviços | EXCLUIR | `backend/app/deprecated_module.py` | Remover módulo obsoleto |

Payload JSON:

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
