# MCP Server FastAPI - Documentação

## Visão Geral

O `mcp_server_fastapi.py` implementa um servidor FastAPI robusto para orquestrar workflows de análise e geração de código usando agentes de IA. O sistema gerencia jobs assíncronos, aprovações manuais, geração de relatórios e integração com diferentes tipos de repositórios (GitHub, GitLab, Azure DevOps).

## Arquitetura do Sistema

### Componentes Principais

- **FastAPI Server**: API REST para comunicação externa
- **Job Store (Redis)**: Armazenamento persistente de jobs e estados
- **Workflow Orchestrator**: Orquestrador de workflows de análise
- **Dependency Container**: Injeção de dependências e serviços
- **Analysis Name Service**: Gerenciamento de nomes de análises

### Estados de Job

| Estado | Descrição |
|--------|----------|
| `starting` | Job foi criado e está iniciando |
| `pending_approval` | Aguardando aprovação manual do usuário |
| `workflow_started` | Workflow foi aprovado e está executando |
| `completed` | Job finalizado com sucesso |
| `failed` | Job falhou durante execução |
| `rejected` | Job foi rejeitado pelo usuário |

## Fluxo do Workflow

mermaid
flowchart TD
    A[Usuário inicia análise via /start-analysis] -->|Cria Job| B[Job armazenado no Redis]
    B --> C[Workflow Orchestrator executa workflow]
    C --> D{Job requer aprovação?}
    D -- Sim --> E[Job aguarda aprovação via /update-job-status]
    E --> F{Aprovado ou Rejeitado?}
    F -- Aprovado --> G[Workflow continua]
    F -- Rejeitado --> H[Job marcado como rejeitado]
    D -- Não --> G
    G --> I[Job executa análise e/ou gera código]
    I --> J[Relatório gerado]
    J --> K[Usuário consulta relatório via /jobs/{job_id}/report]
    J --> L[Usuário pode iniciar geração de código via /start-code-generation-from-report/{analysis_name}]
    K --> M[Usuário consulta status via /status/{job_id}]


## Endpoints da API

### 1. POST `/start-analysis`

**Descrição**: Inicia uma nova análise de repositório.

**Payload**:

{
  "repo_name": "string",
  "projeto": "string",
  "analysis_type": "enum",
  "branch_name": "string (opcional)",
  "instrucoes_extras": "string (opcional)",
  "usar_rag": "boolean",
  "gerar_relatorio_apenas": "boolean",
  "gerar_novo_relatorio": "boolean",
  "model_name": "string (opcional)",
  "arquivos_especificos": "array (opcional)",
  "analysis_name": "string (opcional)",
  "repository_type": "github|gitlab|azure"
}


**Resposta**:

{
  "job_id": "uuid"
}


### 2. POST `/update-job-status`

**Descrição**: Aprova ou rejeita um job que está aguardando aprovação.

**Payload**:

{
  "job_id": "string",
  "action": "approve|reject",
  "instrucoes_extras": "string (opcional)"
}


### 3. GET `/jobs/{job_id}/report`

**Descrição**: Obtém o relatório de análise de um job específico.

**Resposta**:

{
  "job_id": "string",
  "analysis_report": "string",
  "report_blob_url": "string (opcional)"
}


### 4. GET `/analyses/by-name/{analysis_name}`

**Descrição**: Busca um relatório de análise pelo nome da análise.

**Resposta**:

{
  "job_id": "string",
  "analysis_name": "string",
  "analysis_report": "string",
  "report_blob_url": "string (opcional)"
}


### 5. POST `/start-code-generation-from-report/{analysis_name}`

**Descrição**: Inicia a geração de código baseada em um relatório de análise existente.

**Resposta**:

{
  "job_id": "uuid"
}


### 6. GET `/status/{job_id}`

**Descrição**: Consulta o status final e detalhes de um job.

**Resposta**:

{
  "job_id": "string",
  "status": "string",
  "summary": [
    {
      "pull_request_url": "string",
      "branch_name": "string",
      "arquivos_modificados": ["string"]
    }
  ],
  "error_details": "string (opcional)",
  "analysis_report": "string (opcional)",
  "diagnostic_logs": "object (opcional)",
  "report_blob_url": "string (opcional)"
}


## Tipos de Repositório Suportados

### GitHub
- Formato: `owner/repository`
- Exemplo: `microsoft/vscode`

### GitLab
- **Recomendado**: Project ID numérico (ex: `123456`)
- **Alternativo**: Path completo `namespace/projeto` (ex: `meugrupo/meuprojeto`)
- **Validação**: O sistema normaliza automaticamente o formato GitLab

### Azure DevOps
- Formato padrão do Azure DevOps

## Funcionalidades Especiais

### Normalização de Repositórios GitLab

O sistema possui validação especial para repositórios GitLab:
- Aceita Project ID numérico (mais robusto)
- Valida formato de path `namespace/projeto`
- Rejeita formatos inválidos com mensagens de erro claras

### Geração Automática de Nomes de Análise

Quando não fornecido, o sistema gera automaticamente um nome único:

analysis-{uuid-8-chars}


### Modo Relatório Apenas

Quando `gerar_relatorio_apenas: true`, o job:
- Executa apenas a análise
- Não gera código
- Retorna resposta simplificada no status

### Derivação de Jobs

O endpoint `/start-code-generation-from-report` cria um novo job derivado:
- Usa o relatório do job original como instrução
- Configura automaticamente para `analysis_type: 'implementacao'`
- Gera nome de análise derivado: `{original-name}-implementation`

## Estrutura de Dados

### JobFields (Campos do Job)

python
class JobFields:
    STATUS = 'status'
    DATA = 'data'
    ERROR_DETAILS = 'error_details'
    REPO_NAME = 'repo_name'
    ORIGINAL_REPO_NAME = 'original_repo_name'
    PROJETO = 'projeto'
    BRANCH_NAME = 'branch_name'
    ORIGINAL_ANALYSIS_TYPE = 'original_analysis_type'
    INSTRUCOES_EXTRAS = 'instrucoes_extras'
    MODEL_NAME = 'model_name'
    USAR_RAG = 'usar_rag'
    GERAR_RELATORIO_APENAS = 'gerar_relatorio_apenas'
    GERAR_NOVO_RELATORIO = 'gerar_novo_relatorio'
    ARQUIVOS_ESPECIFICOS = 'arquivos_especificos'
    ANALYSIS_NAME = 'analysis_name'
    REPOSITORY_TYPE = 'repository_type'
    ANALYSIS_REPORT = 'analysis_report'
    REPORT_BLOB_URL = 'report_blob_url'
    COMMIT_DETAILS = 'commit_details'
    DIAGNOSTIC_LOGS = 'diagnostic_logs'
    INSTRUCOES_EXTRAS_APROVACAO = 'instrucoes_extras_aprovacao'
    PAUSED_AT_STEP = 'paused_at_step'
    SUCCESS = 'success'
    PR_URL = 'pr_url'
    ARQUIVOS_MODIFICADOS = 'arquivos_modificados'


## Tratamento de Erros

### Validações Principais

1. **Job não encontrado**: HTTP 404
2. **Job não aguardando aprovação**: HTTP 400
3. **Formato de repositório GitLab inválido**: HTTP 400
4. **Análise não encontrada**: HTTP 404
5. **Relatório não encontrado**: HTTP 404

### Logs de Diagnóstico

O sistema mantém logs detalhados em `diagnostic_logs` para:
- Debugging de problemas
- Rastreamento de execução
- Análise de performance

## Middleware e Configurações

### CORS
- Configurado para aceitar todas as origens (`*`)
- Permite todos os métodos e headers
- Credentials habilitado

### Versioning
- Versão atual: `9.0.0`
- Título: "MCP Server - Multi-Agent Code Platform"

## Background Tasks

O sistema utiliza FastAPI Background Tasks para:
- Execução assíncrona de workflows
- Não bloquear requisições HTTP
- Permitir processamento paralelo de múltiplos jobs

## Integração com Serviços

### Dependency Container
- `WorkflowOrchestrator`: Execução de workflows
- `JobStore`: Persistência de jobs
- `AnalysisNameService`: Gerenciamento de nomes
- `WorkflowRegistryService`: Registro de tipos de análise

### Redis
- Armazenamento de jobs
- Persistência de estado
- Suporte a TTL para limpeza automática