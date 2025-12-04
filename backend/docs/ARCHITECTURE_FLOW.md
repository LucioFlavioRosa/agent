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
    AA -->|Envia para MCP (sempre com session_id)| AF
    AF -->|session_id| AA
    AF -->|Webhooks Progresso/Conclusão (session_id)| AA
    AA -->|Atualiza Relatórios| AD
    AD -->|Salva Estado| AE
    AG -->|Salvamento Periódico| AE
    AC -->|Carrega Segredos| AA


---

## Etapas do Fluxo e Código Responsável

### 1. Login e Autenticação via Azure AD
- O frontend envia o token JWT via header `Authorization`. O backend valida o token, extrai o `usuario_executor` e retorna a lista de projetos do usuário.
- O backend gera um novo `session_id` a cada login e retorna ao frontend.
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
- O backend sempre envia o `session_id` para o MCP e espera que o MCP retorne o mesmo `session_id` em todas as respostas e webhooks.
- Código:
  - `backend/app/api/analysis.py` (`/analysis/start`)
  - `backend/app/services/blob_storage_service.py` (`upload_and_extract_docx`)
  - `backend/app/services/docx_parser_service.py` (`extract_text_from_docx`)

### 4. Criação e Gerenciamento de Sessão no Redis
- Sessões são criadas e persistidas no Redis, incluindo campos como `comentario_usuario`, `extracted_text`, `project_id`, `docx_files` e `reports`.
- O único identificador de sessão é o `session_id`, gerado no login.
- Código:
  - `backend/app/services/redis_session_service.py` (`create_session`, `add_docx_file`, `update_session_extracted_text`, `update_report`, `restore_session_from_state`, `get_session_by_project`)
  - `backend/app/models/session_models.py` (`SessionData`)

### 5. Salvamento Automático e Periódico de Estado no Blob Storage
- Estados de sessão/projeto são salvos periodicamente no Blob Storage via `BackgroundStateSaver`. Mudanças em relatórios ou estado acionam o salvamento automático.
- Cada novo estado é salvo como um novo arquivo, nunca sobrescrevendo o anterior.
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
- O backend envia payloads para o MCP (sempre com texto extraído, nunca URL). O campo `session_id` é sempre enviado e deve ser retornado pelo MCP em todas as respostas e webhooks.
- O backend nunca espera que o MCP gere um identificador próprio.
- Persistência do session_id: O session_id é gerado no login e usado em todas as etapas.
- Busca do estado: Sempre que for buscar o estado mais atual de uma sessão, utiliza-se o session_id e pega-se o arquivo mais recente (por timestamp) no Blob Storage.
- Código:
  - `backend/app/services/mcp_client_service.py` (`start_analysis`)
  - `backend/app/api/analysis.py` (envio do session_id ao MCP)
  - `backend/app/api/webhooks.py` (busca sessão por session_id no webhook)

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
    BE-->>FE: Lista de projetos + session_id
    FE->>BE: POST /analysis/start (arquivo, projeto, analysis_type, ...)
    BE->>BS: Salva arquivo (em paralelo)
    BE->>BE: Extrai texto (em paralelo)
    BE->>RS: Cria sessão (usa session_id do login)
    BE->>MCP: Envia payload (texto extraído, inclui session_id)
    MCP-->>BE: status, session_id (deve ser o mesmo recebido)
    BE->>BS: Salva estado inicial (session_id)
    BE-->>FE: status, session_id


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
    BE->>RS: Restaura sessão do estado (usa session_id)
    BE->>MCP: Envia payload (texto extraído do estado, inclui session_id)
    MCP-->>BE: status, session_id (deve ser o mesmo recebido)
    BE->>BS: Salva estado (session_id)
    BE-->>FE: status, session_id


### 3. Fluxo de Atualização de Relatório
mermaid
sequenceDiagram
    MCP->>BE: Webhook (session_id, status, report_type, report_data)
    BE->>RS: update_report (salva relatório no Redis)
    RS->>PS: save_state_to_blob (salva estado imediatamente)
    PS->>BS: Persistência no Blob Storage (novo arquivo, nunca sobrescreve)
    BE->>BS: (opcional) Salvamento redundante imediato após webhook


### 4. Fluxo de Erro e Recuperação
mermaid
sequenceDiagram
    BE->>MCP: start_analysis (envia session_id)
    MCP-->>BE: status: error, error_message, session_id
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
- O único identificador usado em toda a comunicação é o `session_id`, gerado no login e persistido em todas as etapas do fluxo.
- O MCP nunca gera nenhum identificador próprio: sempre recebe e retorna o `session_id` enviado pelo backend.
- Quando for buscar o estado mais atual de uma sessão, deve-se usar o `session_id` e pegar o estado mais recente (por timestamp, se houver múltiplos arquivos no Blob).
- O backend nunca atualiza um registro de sessão já salvo: sempre cria um novo estado com os dados atualizados da sessão.
- Após cada atualização de relatório via webhook do MCP, o estado é salvo imediatamente no Blob Storage e o Redis é atualizado, garantindo consistência e minimizando perda de dados em caso de falha.
- O endpoint `/projects/check` sempre retorna o estado mais recente disponível, priorizando o Redis.
