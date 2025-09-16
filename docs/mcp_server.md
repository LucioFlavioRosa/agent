# MCP Server FastAPI - Documentação

## Visão Geral

O **MCP Server FastAPI** é um servidor robusto que orquestra agentes de IA para análise e implementação de código. Ele utiliza Redis para gerenciamento de jobs e oferece uma API REST completa para iniciar análises, aprovar workflows e consultar resultados.

## Arquitetura Principal

### Classes de Controle

- **JobStatus**: Define os estados possíveis de um job
  - `STARTING`: Job iniciado
  - `PENDING_APPROVAL`: Aguardando aprovação manual
  - `WORKFLOW_STARTED`: Workflow em execução
  - `COMPLETED`: Concluído com sucesso
  - `FAILED`: Falhou durante execução
  - `REJECTED`: Rejeitado pelo usuário

- **JobFields**: Constantes para campos de dados dos jobs
- **JobActions**: Ações disponíveis (`APPROVE`, `REJECT`)

### Modelos de Dados (Pydantic)

- **StartAnalysisPayload**: Payload para iniciar análise
- **UpdateJobPayload**: Payload para aprovar/rejeitar jobs
- **FinalStatusResponse**: Resposta completa de status
- **PullRequestSummary**: Resumo de Pull Requests criados
- **ReportResponse**: Resposta com relatório de análise
- **AnalysisByNameResponse**: Resposta de análise por nome

## Fluxo de Trabalho

mermaid
flowchart TD
    A[Cliente POST /start-analysis] --> B[Validação e Normalização do Repo]
    B --> C[Geração de Job ID único]
    C --> D[Criação de dados iniciais do job]
    D --> E[Armazenamento no Job Store]
    E --> F[Registro do nome da análise]
    F --> G[Execução do workflow em background]
    
    G --> H{Workflow precisa de aprovação?}
    H -->|Sim| I[Status: PENDING_APPROVAL]
    H -->|Não| J[Continua execução]
    
    I --> K[Cliente POST /update-job-status]
    K --> L{Ação do usuário}
    L -->|APPROVE| M[Status: WORKFLOW_STARTED]
    L -->|REJECT| N[Status: REJECTED]
    
    M --> O[Retoma workflow do passo pausado]
    O --> J
    
    J --> P{Execução bem-sucedida?}
    P -->|Sim| Q[Status: COMPLETED]
    P -->|Não| R[Status: FAILED]
    
    Q --> S[Geração de relatórios]
    S --> T[Criação de Pull Requests]
    T --> U[Cliente GET /status/{job_id}]
    
    R --> V[Logs de diagnóstico]
    V --> U
    
    N --> U
    
    U --> W[Resposta final com status e resultados]
    
    X[Cliente GET /jobs/{job_id}/report] --> Y[Retorna relatório específico]
    Z[Cliente GET /analyses/by-name/{name}] --> AA[Busca análise por nome]
    BB[Cliente POST /start-code-generation-from-report/{name}] --> CC[Cria novo job baseado em relatório existente]


## Endpoints da API

### 1. POST /start-analysis
**Descrição**: Inicia uma nova análise de código

**Parâmetros**:
- `repo_name`: Nome do repositório
- `projeto`: Nome do projeto para agrupamento
- `analysis_type`: Tipo de análise (validado dinamicamente)
- `branch_name`: Branch específica (opcional)
- `instrucoes_extras`: Instruções adicionais (opcional)
- `usar_rag`: Usar RAG (Retrieval-Augmented Generation)
- `gerar_relatorio_apenas`: Apenas gerar relatório
- `gerar_novo_relatorio`: Forçar novo relatório
- `model_name`: Modelo LLM específico (opcional)
- `arquivos_especificos`: Lista de arquivos específicos (opcional)
- `analysis_name`: Nome personalizado da análise (opcional)
- `repository_type`: Tipo do repositório (`github`, `gitlab`, `azure`)

**Resposta**: `{"job_id": "uuid"}`

### 2. POST /update-job-status
**Descrição**: Aprova ou rejeita um job pendente

**Parâmetros**:
- `job_id`: ID do job
- `action`: `"approve"` ou `"reject"`
- `instrucoes_extras`: Instruções adicionais para aprovação (opcional)

### 3. GET /status/{job_id}
**Descrição**: Consulta o status completo de um job

**Resposta**:
- Status atual
- Lista de Pull Requests criados (se aplicável)
- Relatório de análise
- Logs de diagnóstico
- URL do relatório no Blob Storage

### 4. GET /jobs/{job_id}/report
**Descrição**: Obtém apenas o relatório de um job específico

### 5. GET /analyses/by-name/{analysis_name}
**Descrição**: Busca uma análise pelo nome personalizado

### 6. POST /start-code-generation-from-report/{analysis_name}
**Descrição**: Cria um novo job de implementação baseado no relatório de uma análise existente

## Funcionalidades Especiais

### Normalização de Repositórios GitLab
O sistema possui validação especial para repositórios GitLab:
- Aceita Project ID numérico (recomendado)
- Aceita formato `namespace/projeto`
- Valida e normaliza automaticamente

### Geração Automática de Nomes
Se não fornecido, o sistema gera automaticamente um nome único para a análise no formato `analysis-{uuid8}`.

### Tratamento de Respostas por Tipo
O endpoint `/status/{job_id}` retorna diferentes estruturas baseadas no tipo de job:
- **Relatório apenas**: Retorna apenas o relatório e URL do blob
- **Implementação completa**: Retorna lista de PRs criados, arquivos modificados e logs

### Recuperação de Pull Requests
O sistema busca informações de PRs em múltiplas fontes:
1. `commit_details` (fonte primária)
2. `diagnostic_logs.final_result` (fonte secundária)
3. `diagnostic_logs.penultimate_result` (fallback)

## Dependências Principais

- **FastAPI**: Framework web principal
- **Pydantic**: Validação de dados
- **Redis**: Armazenamento de jobs (via DependencyContainer)
- **UUID**: Geração de IDs únicos
- **CORS**: Middleware para requisições cross-origin

## Tratamento de Erros

O sistema possui validação robusta com mensagens de erro específicas:
- Validação de formato de repositório
- Verificação de existência de jobs
- Validação de estados para aprovação
- Tratamento de erros de validação Pydantic

## Logs e Diagnóstico

Todos os jobs mantêm logs detalhados em `diagnostic_logs` para facilitar debugging e auditoria das operações realizadas.