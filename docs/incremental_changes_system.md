# Sistema de Aplicação Incremental de Mudanças de Código

## Visão Geral

O sistema de aplicação incremental permite que mudanças de código descritas em relatórios de implementação sejam aplicadas de forma automática, sequencial e inteligente, com validação e commits atômicos. Ele foi projetado para lidar com grandes volumes de tarefas, paralelizar mudanças independentes e garantir qualidade por meio de testes automatizados.

## Suporte à Exclusão de Arquivos

O sistema agora suporta operações de exclusão de arquivos. Para especificar uma exclusão, inclua uma entrada no plano de implementação ou relatório com:


{
  "caminho_do_arquivo": "backend/app/deprecated_module.py",
  "status": "DELETE",
  "conteudo": null,
  "justificativa": "Remoção de módulo obsoleto."
}


A exclusão será propagada por todo o pipeline, incluindo committers de GitHub, GitLab e Azure DevOps, bem como no sistema incremental. O rollback de exclusões irá restaurar o arquivo original a partir do cache de contexto.

## Arquitetura

- **Parser de Relatório:** Extrai tarefas de código do relatório markdown, incluindo exclusões.
- **Analisador de Dependências:** Constrói grafo de dependências entre tarefas, valida impacto de exclusões.
- **Cache de Contexto:** Otimiza leituras de arquivos do repositório e armazena conteúdo para rollback.
- **Executor de Mudança:** Aplica cada tarefa individualmente via LLM, incluindo exclusão.
- **Committer Incremental:** Cria commits atômicos por tarefa ou grupo, processando exclusões.
- **Orquestrador:** Gerencia execução sequencial/paralela e checkpoints, incluindo exclusão.

## Fluxo de Execução

1. Relatório de implementação é gerado.
2. Parser extrai tarefas de código, incluindo exclusões.
3. Analisador constrói grafo de dependências e sugere ordem ótima de execução.
4. Orquestrador executa tarefas em ordem, paralelizando grupos independentes.
5. Executor aplica cada mudança via LLM com contexto reduzido, incluindo exclusão.
6. Mudança é validada por testes automatizados.
7. Commit incremental é criado, incluindo exclusões.
8. Checkpoints são salvos para retomada em caso de falha.
9. Workflow segue para aprovação e PR.

## Exemplos de Relatórios

Relatório válido com exclusão:

| Passo # | Camada | Ação | Caminho do Arquivo | Descrição |
|---|---|---|---|---|
| 1 | Domínio | CRIAR | `domain/models/rbac_models.py` | Criar modelo RBAC |
| 2 | Serviços | MODIFICAR | `services/rbac_service.py` | Adicionar lógica de autorização |
| 3 | Infraestrutura | EXCLUIR | `backend/app/deprecated_module.py` | Remover módulo obsoleto |
