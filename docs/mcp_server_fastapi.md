# Funcionamento do MCP Server FastAPI

## 1. Diagrama de Fluxo (Mermaid)

### Fluxo Completo: Iniciar Análise → Executar Workflow → Retornar Resultado

mermaid
flowchart TD
    A[Cliente HTTP] -->|POST /start-analysis| B[FastAPI Endpoint]
    B --> C{Validar Payload}
    C -->|Inválido| D[Retornar Erro 422]
    C -->|Válido| E[Normalizar Nome do Repositório]
    E --> F[Gerar job_id e analysis_name]
    F --> G[Criar Job no Redis]
    G --> H[Registrar Análise]
    H --> I[Disparar Workflow em Background]
    I --> J[Retornar job_id ao Cliente]
    
    I --> K[WorkflowOrchestrator]
    K --> L{Executar Step 1: Ler Código}
    L --> M[RepositoryReader]
    M --> N{Código Lido com Sucesso?}
    N -->|Não| O[Atualizar Job: FAILED]
    N -->|Sim| P{Executar Step 2: Analisar com LLM}
    P --> Q[LLMProvider - Claude/OpenAI]
    Q --> R{Análise Concluída?}
    R -->|Não| O
    R -->|Sim| S{Executar Step 3: Gerar Relatório}
    S --> T[Salvar Relatório no Blob Storage]
    T --> U{gerar_relatorio_apenas?}
    U -->|Sim| V[Atualizar Job: COMPLETED]
    U -->|Não| W{Executar Step 4: Criar PR}
    W --> X[RepositoryCommitter]
    X --> Y{PR Criado?}
    Y -->|Não| O
    Y -->|Sim| V
    
    V --> Z[Cliente Consulta Status]
    Z -->|GET /status/{job_id}| AA[Retornar Resultado Final]
    
    style B fill:#4CAF50,color:#fff
    style K fill:#2196F3,color:#fff
    style Q fill:#FF9800,color:#fff
    style X fill:#9C27B0,color:#fff
    style V fill:#4CAF50,color:#fff
    style O fill:#F44336,color:#fff


### Fluxo de Aprovação Manual

mermaid
flowchart TD
    A[Workflow Pausado] -->|Status: AWAITING_APPROVAL| B[Cliente Revisa Relatório]
    B --> C{Decisão}
    C -->|Aprovar| D[POST /update-job-status - action: approve]
    C -->|Rejeitar| E[POST /update-job-status - action: reject]
    
    D --> F[Atualizar Status: WORKFLOW_STARTED]
    F --> G[Retomar Workflow no Step Pausado + 1]
    G --> H[Executar Steps Restantes]
    H --> I[Criar Pull Request]
    I --> J[Status: COMPLETED]
    
    E --> K[Atualizar Status: REJECTED]
    K --> L[Encerrar Processamento]
    
    style D fill:#4CAF50,color:#fff
    style E fill:#F44336,color:#fff
    style J fill:#4CAF50,color:#fff
    style K fill:#F44336,color:#fff


### Fluxo de Geração de Código a Partir de Relatório

mermaid
flowchart TD
    A[Cliente] -->|POST /start-code-generation-from-report/{analysis_name}| B[Buscar Job Original]
    B --> C{Job Existe?}
    C -->|Não| D[Retornar Erro 404]
    C -->|Sim| E[Recuperar Relatório do Job Original]
    E --> F[Criar Novo Job Derivado]
    F --> G[Copiar Configurações do Job Original]
    G --> H[Definir gerar_relatorio_apenas = False]
    H --> I[Definir gerar_novo_relatorio = False]
    I --> J[Salvar Novo Job no Redis]
    J --> K[Disparar Workflow em Background]
    K --> L[Executar Steps de Geração de Código]
    L --> M[Criar Pull Request]
    M --> N[Status: COMPLETED]
    
    style B fill:#2196F3,color:#fff
    style F fill:#FF9800,color:#fff
    style M fill:#9C27B0,color:#fff
    style N fill:#4CAF50,color:#fff


---

## 2. Explicação do Código `mcp_server_fastapi.py`

O arquivo `mcp_server_fastapi.py` serve como ponto de entrada da API REST do MCP (Multi-Agent Code Platform). Ele expõe endpoints HTTP para iniciar e gerenciar análises de código, consultar status e relatórios, e acionar workflows de geração de código.

### Componentes e Fluxos Principais

- **Dependency Injection:** O `DependencyContainer` centraliza a criação de serviços e suas dependências, facilitando manutenção e testes.
- **Factory Pattern:** Serviços como `ApiServiceFactory` e `WorkflowRegistryService` encapsulam a lógica de criação de objetos complexos.
- **Service Layer:** Lógica de negócio está isolada em serviços especializados (`JobDataService`, `JobValidationService`, `ResponseBuilderService`, etc.).
- **Background Tasks:** Workflows são executados de forma assíncrona usando `BackgroundTasks` do FastAPI.

### Endpoints Principais

- **POST /start-analysis**: Inicia uma nova análise de código. Valida o payload, normaliza o nome do repositório, gera identificadores, cria o job no Redis, registra a análise e dispara o workflow em background.
- **POST /update-job-status**: Aprova ou rejeita um job pausado. Atualiza o status do job e pode retomar o workflow do ponto onde parou.
- **GET /status/{job_id}**: Consulta o status atual de um job, podendo retornar relatório, URL do Blob Storage e informações de Pull Request.
- **GET /jobs/{job_id}/report**: Recupera o relatório de análise de um job específico.
- **GET /analyses/by-name/{analysis_name}**: Busca análise pelo nome, retornando relatório e informações associadas.
- **POST /start-code-generation-from-report/{analysis_name}**: Cria um novo job de geração de código a partir de um relatório existente, copiando configurações do job original e disparando um novo workflow.

### Serviços e Utilitários

- **JobStore:** Armazena o estado dos jobs (status, dados, resultados intermediários) em Redis.
- **WorkflowOrchestrator:** Executa sequencialmente os steps de um workflow, delegando a execução de cada step para um StepExecutor específico.
- **JobDataService:** Cria e manipula estruturas de dados de jobs.
- **JobValidationService:** Valida estados e transições de jobs.
- **ResponseBuilderService:** Constrói respostas HTTP padronizadas.
- **RepositoryNormalizerService:** Normaliza nomes de repositórios.
- **LoggingService:** Centraliza logs estruturados.

### Observações

- O código utiliza validação automática de payloads via Pydantic.
- O CORS está aberto para todas as origens (atenção em produção).
- O uso de background tasks permite que a API seja responsiva mesmo para operações longas.
- O design modular facilita a extensão para novos tipos de análise, steps e provedores de repositório.

---

Para detalhes mais aprofundados sobre cada componente, consulte também o arquivo `docs/ARCHITECTURE.md`.
