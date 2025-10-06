# Documentação do Workflow Principal - MCP Server

## Visão Geral

O MCP Server utiliza um sistema de orquestração de workflows para automatizar e controlar o processamento de jobs de análise e geração de código por agentes de IA. O componente central desse fluxo é o `WorkflowOrchestrator`, responsável por executar etapas (steps) definidas em arquivos de workflow YAML, gerenciar o estado dos jobs, lidar com relatórios e aprovações, e acionar serviços auxiliares.

Esta documentação detalha o funcionamento do workflow principal, ilustrando o fluxo de execução, os pontos de decisão e os principais componentes envolvidos.

---

## Componentes Envolvidos

- **WorkflowOrchestrator**: Classe principal que executa o workflow de acordo com o tipo de análise solicitado.
- **WorkflowRegistryService/Loader**: Carrega e disponibiliza os workflows definidos em YAML.
- **JobHandler**: Gerencia o estado e os dados dos jobs.
- **ReportHandler**: Lê, valida e armazena relatórios de análise.
- **CommitHandler**: Realiza commits das alterações geradas.
- **StepStrategyFactory**: Cria estratégias para execução de cada etapa do workflow.
- **Repository Providers/Readers**: Abstraem o acesso aos repositórios GitHub, GitLab ou Azure.

---

## Fluxo Geral do Workflow

1. **Recebimento do Job**: O usuário inicia uma análise via API (`/start-analysis`), informando o tipo de análise, repositório, branch, etc.
2. **Registro e Normalização**: O job é registrado, os nomes de repositório são normalizados e um identificador único é gerado.
3. **Execução do Workflow**: O `WorkflowOrchestrator` é chamado para executar o workflow correspondente ao tipo de análise.
4. **Execução dos Steps**: Cada etapa (step) do workflow é executada sequencialmente. Para cada step:
   - O status do job é atualizado.
   - Parâmetros específicos do step e do job são preparados.
   - O agente apropriado é chamado (ex: processador, revisor, comparador).
   - O resultado do step é salvo.
   - Se for o primeiro step e houver relatório existente, ele pode ser lido do Blob Storage.
   - Se o step exigir aprovação, o workflow é pausado até a aprovação manual.
   - Se o workflow estiver em modo "gerar_relatorio_apenas", pode ser finalizado após o relatório.
5. **Finalização**: Após todos os steps, o workflow pode:
   - Salvar o relatório final no Blob Storage.
   - Realizar commits das alterações no repositório.
   - Atualizar o status do job para "completed".
6. **Erros**: Qualquer exceção é capturada e o status do job é atualizado para "failed".

---

## Diagrama de Fluxo (Mermaid)

```mermaid
flowchart TD
    %% Etapa 1: Definição de todos os Nós
    A[Início: Recebimento do Job via API]
    B[Registro do Job e Normalização]
    C[Carregamento do Workflow YAML]
    D{Step Atual < Steps Totais?}
    E[Executa Step Atual]
    F{Step exige aprovação?}
    G[Pausa workflow e aguarda aprovação]
    H[Recebe aprovação]
    I{Modo gerar_relatorio_apenas?}
    J{Relatório válido?}
    K[Finaliza workflow (completed)]
    L[Finaliza workflow: Salva relatório, realiza commits, status completed]
    M[Fim]
    N[Atualiza status para failed]

    %% Etapa 2: Definição de todas as Conexões
    A --> B
    B --> C
    C --> D
    D -- Sim --> E
    D -- Não --> L
    D -- Erro --> N
    E --> F
    F -- Sim --> G
    F -- Não --> I
    G --> H
    H --> D
    I -- Sim --> J
    I -- Não --> D
    J -- Sim --> K
    J -- Não --> E
    L --> M
    N --> M
```

---

## Pontos de Decisão Importantes

- **Aprovação Manual**: Alguns steps podem exigir aprovação manual para prosseguir. O workflow é pausado e só continua após aprovação via API.
- **Modo "gerar_relatorio_apenas"**: Se ativado, o workflow finaliza após a geração e validação do relatório, sem executar etapas de commit.
- **Leitura de Relatório Existente**: O sistema tenta reutilizar relatórios já gerados, evitando processamento desnecessário.

---

## Exemplos de Payloads

### Início de Análise (`/start-analysis`)
```json
{
  "repo_name_modernizado": "org/projeto",
  "branch_name_modernizado": "main",
  "projeto": "MeuProjeto",
  "analysis_type": "modernizacao",
  "repository_type": "github"
}
```

### Resposta
```json
{
  "job_id": "uuid-gerado"
}
```

---

## Observações

- O fluxo é altamente configurável via arquivos de workflow YAML, permitindo adicionar, remover ou modificar steps sem alterar o código-fonte.
- O uso de estratégias e handlers especializados torna o sistema modular e fácil de estender.
- O diagrama acima representa o fluxo padrão; workflows customizados podem adicionar etapas ou decisões adicionais.

---

## Referências
- Código-fonte: `services/workflow_orchestrator.py`, `services/workflow_registry_loader.py`, `services/workflow_registry_service.py`
- Definições de workflow: `workflows.yaml`
