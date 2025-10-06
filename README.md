# Multi-Agent Code Platform (MCP)

## Visão Geral

O MCP é uma plataforma robusta para automação de análises e modernização de código, orquestrando agentes inteligentes via API REST construída com FastAPI. O sistema utiliza Redis para armazenamento de jobs e suporta integração com múltiplos provedores de repositório (GitHub, GitLab, Azure DevOps) e modelos LLM (Claude, OpenAI).

## Arquitetura do Sistema

A estrutura do MCP segue princípios de arquitetura limpa, com separação clara de responsabilidades entre agentes, serviços, ferramentas e domínio. Os principais diretórios são:

- `agents/`: Implementações dos agentes de processamento, revisão e comparação de código.
- `services/`: Serviços de negócio e infraestrutura (ex: orquestração de workflow, manipulação de jobs, integração com LLMs).
- `tools/`: Utilitários e integrações com provedores externos (repositórios, storage, secrets).
- `domain/`: Interfaces e contratos para abstração de dependências.

### Padrões de Design Utilizados

- **Dependency Injection:** Centralizado no `DependencyContainer`, facilita testes e extensibilidade.
- **Factory Pattern:** Utilizado para criação de serviços complexos e provedores.
- **Service Layer:** Lógica de negócio isolada em serviços especializados.
- **Background Tasks:** Execução assíncrona de workflows via FastAPI.

## Diagrama de Fluxo (Mermaid)

### Funcionamento Principal do MCP

```mermaid
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
```

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


## Explicação do Código Principal (`mcp_server_fastapi.py`)

### Função

O arquivo `mcp_server_fastapi.py` é o ponto de entrada da API REST do MCP. Ele expõe endpoints para:

- Iniciar novas análises de código
- Gerenciar aprovação/rejeição de jobs
- Consultar status e relatórios
- Gerar código a partir de relatórios existentes

### Principais Componentes

- **DependencyContainer:** Centraliza a criação e injeção de dependências (serviços, provedores, etc.).
- **ApiServiceFactory:** Cria instâncias de serviços de negócio.
- **WorkflowOrchestrator:** Executa workflows de análise em background, step a step.
- **JobStore:** Gerencia o estado dos jobs no Redis.
- **JobDataService, JobValidationService, ResponseBuilderService:** Serviços especializados para manipulação, validação e resposta de jobs.

### Fluxo de Início de Análise (`/start-analysis`)

1. Recebe payload validado pelo Pydantic.
2. Normaliza o nome do repositório.
3. Gera identificadores (`job_id`, `analysis_name`).
4. Cria o job inicial no Redis.
5. Registra a análise para consultas futuras.
6. Dispara o workflow em background.
7. Retorna o `job_id` ao cliente.

### Fluxo de Aprovação/Rejeição (`/update-job-status`)

- Aprovação: Atualiza status, salva instruções extras e retoma o workflow.
- Rejeição: Atualiza status para rejeitado e encerra o processamento.

### Consulta de Status (`/status/{job_id}`)

- Retorna status atual, relatório e informações de Pull Request, se disponíveis.

### Segurança e Performance

- **CORS:** Aberto por padrão (recomenda-se restringir em produção).
- **Validação:** Pydantic previne dados inválidos.
- **Execução Assíncrona:** Workflows não bloqueiam a API.
- **Redis:** Armazenamento rápido para jobs.

---

## Troubleshooting (Resolução de Problemas)

### Erros Comuns

- **Erro de conexão com Redis:**
  - Verifique se o serviço Redis está ativo e as variáveis de ambiente de conexão estão corretas.
- **Falha de autenticação com provedores Git:**
  - Confirme se os tokens/secrets estão configurados corretamente no Azure Key Vault ou variáveis de ambiente.
- **Timeouts de LLM:**
  - Ajuste o timeout no serviço de LLM ou aumente os recursos disponíveis.
- **Job não avança de status:**
  - Consulte os logs do WorkflowOrchestrator e verifique se há exceções não tratadas.

---

## Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Mermaid Documentation](https://mermaid-js.github.io/mermaid/#/)
- [Redis Documentation](https://redis.io/)
