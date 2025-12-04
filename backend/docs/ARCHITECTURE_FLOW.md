# Arquitetura e Fluxos do Backend Peers CodeAI

Este documento detalha o fluxo completo do backend Peers CodeAI, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integrações com Azure Key Vault (múltiplos cofres), Blob Storage, Redis, MCP Server e o mecanismo de configuração dinâmica de agentes. Cada etapa está explicada, com referência ao arquivo de código responsável e diagramas ilustrativos.

---

## Diagrama Geral do Fluxo (Mermaid)

mermaid
flowchart TD
    subgraph Frontend
        Z[Usuário/Frontend]
    end
    subgraph API Layer
        AA[FastAPI Routers]
    end
    subgraph Auth
        AB[Auth Middleware & AzureADService]
    end
    subgraph Config
        AC[ConfigLoaderService & AzureSecretManager]
    end
    subgraph State
        AD[ProjectStateService & RedisSessionService]
    end
    subgraph Storage
        AE[Blob Storage Service]
    end
    subgraph MCP
        AF[MCPClientService]
    end
    subgraph Background
        AG[BackgroundStateSaver]
    end
    Z -->|Login| AA
    AA -->|Validação Token| AB
    AB -->|Busca Segredos| AC
    AA -->|Verifica Projeto| AD
    AD -->|Busca Estado| AE
    AA -->|Início de Análise (inclui upload DOCX)| AE
    AE -->|Extrai Texto| AA
    AA -->|Cria Sessão| AD
    AA -->|Envia para MCP| AF
    AF -->|Job ID| AA
    AF -->|Webhooks Progresso/Conclusão| AA
    AA -->|Atualiza Relatórios| AD
    AD -->|Salva Estado| AE
    AG -->|Salvamento Periódico| AE
    AC -->|Carrega Segredos| AA


---

## Etapas do Fluxo e Código Responsável

### 1. Login e Autenticação via Azure AD
- O frontend envia o token JWT via header `Authorization`. O backend valida o token, extrai o `usuario_executor` e retorna a lista de projetos do usuário.
- Código:
  - `backend/app/api/auth.py` (`POST /auth/login`)
  - `backend/app/middleware/auth_middleware.py` (`get_current_user`)
  - `backend/app/services/azure_ad_service.py` (`validate_token`)
  - `backend/app/services/project_state_service.py` (`list_user_projects`)

### 2. Verificação de Projeto Existente
- O frontend chama `/projects/check` para saber se o projeto existe. O backend busca o estado mais recente do projeto **primeiro no Redis** (sessão ativa), e só faz fallback para o Blob Storage se não encontrar no Redis.
- Código:
  - `backend/app/api/projects.py` (`/projects/check`)
  - `backend/app/services/redis_session_service.py` (`get_session_by_project`)
  - `backend/app/services/project_state_service.py` (`load_latest_state_from_redis`, `load_latest_state_from_blob`)

#### Diagrama de Sequência: Consulta de Estado de Projeto

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant RS as RedisSessionService
    participant PS as ProjectStateService
    participant BS as Blob Storage
    FE->>BE: GET /projects/check?projeto=NomeProjeto
    BE->>RS: get_session_by_project(usuario_executor, projeto)
    alt Sessão encontrada no Redis
        RS-->>BE: SessionData
        BE->>PS: load_latest_state_from_redis(session_id)
        PS-->>BE: Estado mais recente (do Redis)
        BE-->>FE: exists: true, state (do Redis)
    else Sessão não encontrada no Redis
        BE->>PS: load_latest_state_from_blob(usuario_executor, projeto)
        PS-->>BE: Estado (do Blob Storage)
        BE-->>FE: exists: true, state (do Blob Storage)
    end
    Note over BE: O campo 'reports' sempre reflete o estado mais recente disponível

### 3. Início de Análise e Upload de DOCX (Processamento Paralelo)
- O upload do arquivo DOCX e a extração do texto ocorrem dentro do endpoint `/analysis/start` via multipart/form-data. O backend retorna tanto a URL do arquivo quanto o texto extraído.
- Código:
  - `backend/app/api/analysis.py` (`/analysis/start`)
  - `backend/app/services/blob_storage_service.py` (`upload_and_extract_docx`)
  - `backend/app/services/docx_parser_service.py` (`extract_text_from_docx`)

### 4. Criação e Gerenciamento de Sessão no Redis
- Sessões são criadas e persistidas no Redis, incluindo campos como `comentario_usuario`, `extracted_text`, `project_id`, `docx_files` e `reports`.
- Código:
  - `backend/app/services/redis_session_service.py` (`create_session`, `add_docx_file`, `update_session_extracted_text`, `update_report`, `restore_session_from_state`, `get_session_by_project`)
  - `backend/app/models/session_models.py` (`SessionData`)

### 5. Salvamento Automático e Periódico de Estado no Blob Storage
- Estados de sessão/projeto são salvos periodicamente no Blob Storage via `BackgroundStateSaver`. Mudanças em relatórios ou estado acionam o salvamento automático.
- Código:
  - `backend/app/services/background_state_saver.py` (`schedule_periodic_save`)
  - `backend/app/services/project_state_service.py` (`save_state_to_blob`)
  - `backend/app/services/redis_session_service.py` (`update_session_on_state_change`)

### 6. Carregamento de Segredos do Key Vault (Múltiplos Cofres)
- Segredos sensíveis são carregados de múltiplos Key Vaults (Azure, DevOps, GitHub, LLM) via Managed Identity. Existe fallback para variáveis de ambiente.
- Código:
  - `backend/app/services/config_loader_service.py` (`load_secrets_from_key_vault`)
  - `backend/app/services/azure_secret_manager.py` (`AzureSecretManager`)
  - `backend/app/core/config.py` (`Settings`)

### 7. Configuração Dinâmica de Agentes MCP
- Arquivo: `backend/config/mcp_agents.json` define agentes MCP, URLs, campos de relatório e mapeamentos.
- Carregamento: `MCPConfigService.load_config` carrega o JSON na inicialização.
- Roteamento: `MCPClientService.get_mcp_endpoint` seleciona a URL do MCP conforme `analysis_type`.
- Mapeamento de Relatórios: `RedisSessionService.update_report` usa `report_mapping` para salvar relatórios no campo correto.
- Extensibilidade: Novos agentes podem ser adicionados apenas editando o JSON.

### 8. Comunicação Backend ↔ MCP (Incluindo Webhooks)
- O backend envia payloads para o MCP (sempre com texto extraído, nunca URL). MCP responde com `job_id` e envia webhooks de progresso/conclusão, que atualizam relatórios na sessão Redis.
- Persistência do job_id: Após receber o `job_id` do MCP no endpoint `/analysis/start`, o backend persiste imediatamente a relação `job_id -> session_id` no Redis, garantindo que, quando o webhook do MCP chegar, a sessão possa ser encontrada rapidamente usando o `job_id`.
- Busca do job_id no webhook: O endpoint `/webhooks/mcp` recebe o webhook do MCP, busca a sessão correspondente usando o `job_id` persistido no Redis, e atualiza os relatórios da sessão. Se o `job_id` não for encontrado, retorna 404 e loga o erro detalhadamente.
- Código:
  - `backend/app/services/mcp_client_service.py` (`start_analysis`)
  - `backend/app/services/redis_session_service.py` (`update_session_job_id`, `get_session_by_job_id`)
  - `backend/app/api/analysis.py` (chama `update_session_job_id` após início da análise)
  - `backend/app/api/webhooks.py` (busca sessão por `job_id` no webhook)

### 9. Atualização de Relatórios e Propagação de Estado
- Relatórios são atualizados via endpoint ou webhook. Toda atualização aciona o salvamento automático do estado no Blob Storage **e também mantém o estado mais recente no Redis**.
- Após cada atualização de relatório via webhook do MCP, o estado é salvo imediatamente no Blob Storage e o Redis é atualizado, garantindo consistência e minimizando perda de dados em caso de falha.
- O endpoint `/projects/check` sempre retorna o estado mais recente disponível, priorizando o Redis.
- Código:
  - `backend/app/api/session.py` (`PUT /session/{session_id}/report`)
  - `backend/app/services/redis_session_service.py` (`update_report`, `update_session_on_state_change`, `get_session_by_project`)
  - `backend/app/api/projects.py` (consulta primeiro no Redis, depois no Blob Storage)
  - `backend/app/services/project_state_service.py` (`load_latest_state_from_redis`, `load_latest_state_from_blob`)

#### Diagrama do Fluxo de Consulta de Estado Mais Recente

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant RS as RedisSessionService
    participant PS as ProjectStateService
    participant BS as Blob Storage
    FE->>BE: GET /projects/check?projeto=NomeProjeto
    BE->>RS: get_session_by_project(usuario_executor, projeto)
    alt Sessão encontrada no Redis
        RS-->>BE: SessionData
        BE->>PS: load_latest_state_from_redis(session_id)
        PS-->>BE: Estado mais recente (do Redis)
        BE-->>FE: exists: true, state (do Redis)
    else Sessão não encontrada no Redis
        BE->>PS: load_latest_state_from_blob(usuario_executor, projeto)
        PS-->>BE: Estado (do Blob Storage)
        BE-->>FE: exists: true, state (do Blob Storage)
    end

---

## Fluxos Críticos de Negócio

### 1. Fluxo de Novo Projeto
mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant KV as Key Vault
    participant BS as Blob Storage
    participant RS as Redis
    participant MCP as MCP Server
    FE->>BE: POST /auth/login (token)
    BE->>KV: Carrega segredos
    BE->>BS: Lista projetos
    BE-->>FE: Lista de projetos
    FE->>BE: POST /analysis/start (arquivo, projeto, analysis_type, ...)
    BE->>BS: Salva arquivo (em paralelo)
    BE->>BE: Extrai texto (em paralelo)
    BE->>RS: Cria sessão
    BE->>MCP: Envia payload (texto extraído)
    MCP-->>BE: job_id
    BE->>RS: Atualiza sessão (job_id) e persiste relação job_id -> session_id no Redis
    BE->>BS: Salva estado inicial
    BE-->>FE: job_id, session_id, project_id


### 2. Fluxo de Projeto Existente
mermaid
sequenceDiagram
    FE->>BE: GET /projects/check
    BE->>RS: get_session_by_project(usuario_executor, projeto)
    alt Sessão encontrada no Redis
        RS-->>BE: SessionData
        BE->>PS: load_latest_state_from_redis(session_id)
        PS-->>BE: Estado mais recente (do Redis)
        BE-->>FE: exists: true, state (do Redis)
    else Sessão não encontrada no Redis
        BE->>PS: load_latest_state_from_blob(usuario_executor, projeto)
        PS-->>BE: Estado (do Blob Storage)
        BE-->>FE: exists: true, state (do Blob Storage)
    end
    FE->>BE: POST /analysis/start (sem upload)
    BE->>RS: Restaura sessão do estado
    BE->>MCP: Envia payload (texto extraído do estado)
    MCP-->>BE: job_id
    BE->>RS: Atualiza sessão (job_id) e persiste relação job_id -> session_id no Redis
    BE->>BS: Salva estado
    BE-->>FE: job_id, session_id, project_id


### 3. Fluxo de Atualização de Relatório
mermaid
sequenceDiagram
    MCP->>BE: Webhook (job_id, status, report_type, report_data)
    BE->>RS: update_report (salva relatório no Redis)
    RS->>PS: save_state_to_blob (salva estado imediatamente)
    PS->>BS: Persistência no Blob Storage
    BE->>BS: (opcional) Salvamento redundante imediato após webhook


### 4. Fluxo de Erro e Recuperação
mermaid
sequenceDiagram
    BE->>MCP: start_analysis
    MCP-->>BE: status: error, error_message
    BE-->>FE: 502 Bad Gateway, detail
    BE->>KV: get_secret
    KV-->>BE: erro
    BE-->>FE: 503 Service Unavailable, detail
    BE->>RS: get_session
    RS-->>BE: erro
    BE-->>FE: 503 Service Unavailable, detail


---

## Integração com Múltiplos Key Vaults

- O backend suporta múltiplos Key Vaults (Azure, DevOps, GitHub, LLM), roteando segredos conforme o tipo via `AzureSecretManager` e `VaultType`.
- O mapeamento de segredos está documentado em `backend/docs/KEY_VAULT_SECRETS_MAPPING.md`.
- O carregamento ocorre na inicialização via `ConfigLoaderService.load_secrets_from_key_vault`, com cache thread-safe para evitar chamadas repetidas.
- Fallback: Se um segredo não for encontrado no Key Vault, o backend tenta variável de ambiente.
- Validação: Campos obrigatórios são validados por `settings.validate_required_fields`.

mermaid
flowchart LR
    Start((Startup)) --> LoadSecrets[ConfigLoaderService.load_secrets_from_key_vault]
    LoadSecrets -->|Por tipo| AzureSecretManager
    AzureSecretManager -->|Busca segredo| KeyVaults[Azure/DevOps/GitHub/LLM]
    AzureSecretManager -->|Cache| Cache
    KeyVaults -->|Retorna segredo| AzureSecretManager
    AzureSecretManager -->|Fallback| EnvVars[Variáveis de Ambiente]
    AzureSecretManager -->|Seta no settings| Settings


---

## Configuração Dinâmica de Agentes MCP

- Arquivo: `backend/config/mcp_agents.json` define agentes MCP, URLs, campos de relatório e mapeamentos.
- Carregamento: `MCPConfigService.load_config` carrega o JSON na inicialização.
- Roteamento: `MCPClientService.get_mcp_endpoint` seleciona a URL do MCP conforme `analysis_type`.
- Mapeamento de Relatórios: `RedisSessionService.update_report` usa `report_mapping` para salvar relatórios no campo correto.
- Extensibilidade: Novos agentes podem ser adicionados apenas editando o JSON.

**Exemplo de configuração de agente:**

{
  "agents": {
    "criacao_epicos_azure_devops": {
      "agent_name": "Epicos Azure DevOps",
      "mcp_url": "https://mcp-epicos.azurewebsites.net",
      "report_fields": ["epicos_report"],
      "report_mapping": {"epicos": "epicos_report"}
    },
    "features_generation": {
      "agent_name": "Features Generator",
      "mcp_url": "https://mcp-features.azurewebsites.net",
      "report_fields": ["features_report"],
      "report_mapping": {"features": "features_report"}
    }
  }
}


---

## Observações

- O campo `analysis_name` foi removido de todos os fluxos e payloads.
- Para iniciar análise, é obrigatório informar `analysis_type` e pelo menos um de `file` (arquivo DOCX) ou `comentario_usuario`.
- O upload de DOCX ocorre dentro do endpoint `/analysis/start` via multipart/form-data.
- O salvamento de estado no Blob Storage é automático e periódico, disparado por alterações de relatório ou estado.
- O cache de segredos do Key Vault é thread-safe e evita múltiplas chamadas desnecessárias.
- O Redis **deve** ser configurado via Key Vault (não via variáveis de ambiente do App Service).
- Para ambientes com Redis em subrede privada, o App Service deve estar integrado à mesma VNET.
- O sistema pode operar em modo de teste com autenticação mockada (`SKIP_AUTH_FOR_TESTING`), útil para desenvolvimento local.
- Todos os exemplos de payload e resposta estão detalhados em `backend/docs/API_PAYLOAD_EXAMPLES.md`.
- Após o início da análise, a relação job_id -> session_id é persistida no Redis para garantir que o webhook do MCP encontre a sessão correta.
- Após cada atualização de relatório via webhook do MCP, o estado é salvo imediatamente no Blob Storage e o Redis é atualizado, garantindo consistência e minimizando perda de dados em caso de falha.
- O endpoint `/projects/check` sempre retorna o estado mais recente disponível, priorizando o Redis.
