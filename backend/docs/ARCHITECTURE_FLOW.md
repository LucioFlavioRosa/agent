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
    AA -->|Upload DOCX| AE
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
- O frontend chama `/projects/check` enviando o campo `projeto` (nome do projeto). O backend converte internamente para `project_id` usando o método auxiliar, e todas as operações subsequentes usam `project_id` como identificador principal.
- Código:
  - `backend/app/api/projects.py` (`/projects/check`)
  - `backend/app/services/project_state_service.py` (`_get_project_id_by_name`, `load_latest_state_from_blob`)

### 3. Upload de DOCX e Extração de Texto (Processamento Paralelo)
- O upload do arquivo DOCX e a extração do texto ocorrem em paralelo. O backend retorna tanto a URL do arquivo quanto o texto extraído, além de `project_id` e `nome_projeto`.
- Código:
  - `backend/app/api/upload.py` (`/upload/docx`)
  - `backend/app/services/blob_storage_service.py` (`upload_and_extract_docx`)
  - `backend/app/services/docx_parser_service.py` (`extract_text_from_docx`)

### 4. Criação e Gerenciamento de Sessão no Redis
- Sessões são criadas e persistidas no Redis, incluindo campos como `comentario_usuario`, `extracted_text`, `project_id`, `docx_files` e os campos de relatório individuais (`epicos_report`, `features_report`, etc).
- Código:
  - `backend/app/services/redis_session_service.py` (`create_session`, `add_docx_file`, `update_session_extracted_text`, `update_report`, `restore_session_from_state`)
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
- Arquivo: `backend/config/mcp_agents.json` define agentes MCP, URLs e campos de relatório.
- Carregamento: `MCPConfigService.load_config` carrega o JSON na inicialização.
- Roteamento: `MCPClientService.get_mcp_endpoint` seleciona a URL do MCP conforme `analysis_type`.
- Extensibilidade: Novos agentes podem ser adicionados apenas editando o JSON.

### 8. Comunicação Backend ↔ MCP (Incluindo Webhooks)
- O backend envia payloads para o MCP sempre usando `project_id` como identificador principal. O campo `nome_projeto` é enviado apenas para log/debug. O MCP responde com `job_id` e envia webhooks de progresso/conclusão, que atualizam relatórios na sessão Redis usando `project_id`.
- O backend busca a sessão correspondente usando o `project_id` persistido no Redis. O `job_id` é apenas um identificador da execução no MCP, mas não é usado para buscar sessões no backend.
- O campo `report_data` do webhook do MCP deve ser um dicionário com exatamente uma chave, que pode ser: `epicos_report`, `features_report`, `times_descricao_report`, `alocacao_times_report` ou `premissas_riscos_report`. O valor é sempre uma lista de itens do relatório. O backend atualiza diretamente o campo correspondente no estado do projeto/sessão.
- Código:
  - `backend/app/services/mcp_client_service.py` (`start_analysis`)
  - `backend/app/services/redis_session_service.py` (`get_session_by_project_id`, `update_report`)
  - `backend/app/api/analysis.py` (envio do project_id ao MCP)
  - `backend/app/api/webhooks.py` (busca sessão por `project_id` no webhook)

### 9. Atualização de Relatórios e Propagação de Estado
- Relatórios são atualizados via endpoint ou webhook. Toda atualização aciona o salvamento automático do estado no Blob Storage. Cada relatório é salvo em seu campo individual (`epicos_report`, `features_report`, etc).
- Código:
  - `backend/app/api/session.py` (`PUT /session/project/{project_id}/report`)
  - `backend/app/services/redis_session_service.py` (`update_report`, `update_session_on_state_change`)

### 10. Fluxo de Erro e Recuperação
- O sistema lida com falhas do MCP, Key Vault, Redis e Blob Storage, propagando erros padronizados para o frontend.
- Código:
  - Handlers de exceção em todos os endpoints
  - `backend/app/services/startup_validator.py`

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
    FE->>BE: POST /upload/docx (arquivo, projeto)
    BE->>BS: Salva arquivo
    BE->>BE: Extrai texto
    BE->>RS: Cria sessão (com campos de relatório individuais, project_id e nome_projeto)
    BE-->>FE: blob_url, texto extraído, project_id, nome_projeto
    FE->>BE: POST /analysis/start (projeto, analysis_type)
    BE->>BE: Busca ou cria project_id correspondente ao nome do projeto
    BE->>MCP: Envia payload (project_id, nome_projeto, texto extraído)
    MCP-->>BE: job_id, project_id
    BE->>BS: Salva estado inicial
    BE-->>FE: job_id, project_id, nome_projeto

### 2. Fluxo de Projeto Existente
mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (projeto)
    BE->>BE: Busca project_id correspondente ao nome do projeto
    BE->>BS: Busca estado usando project_id
    BE-->>FE: exists: true, state (com campos de relatório individuais, project_id e nome_projeto)
    FE->>BE: POST /analysis/start (projeto, analysis_type)
    BE->>BE: Busca project_id correspondente ao nome do projeto
    BE->>RS: Restaura sessão do estado (com project_id e nome_projeto)
    BE->>MCP: Envia payload (project_id, nome_projeto, texto extraído)
    MCP-->>BE: job_id, project_id
    BE->>BS: Salva estado
    BE-->>FE: job_id, project_id, nome_projeto

### 3. Fluxo de Atualização de Relatório
mermaid
sequenceDiagram
    MCP->>BE: Webhook (job_id, project_id, status, report_data)
    BE->>RS: Busca sessão por project_id (usando relação persistida project_id)
    BE->>RS: Atualiza relatório individual na sessão (ex: epicos_report)
    BE->>BS: Salva estado

### 4. Fluxo de Erro e Recuperação
mermaid
sequenceDiagram
    BE->>MCP: start_analysis
    MCP-->>BE: status: error, error_message, project_id
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

- Arquivo: `backend/config/mcp_agents.json` define agentes MCP, URLs e campos de relatório.
- Carregamento: `MCPConfigService.load_config` carrega o JSON na inicialização.
- Roteamento: `MCPClientService.get_mcp_endpoint` seleciona a URL do MCP conforme `analysis_type`.
- Extensibilidade: Novos agentes podem ser adicionados apenas editando o JSON.

**Exemplo de configuração de agente:**

{
  "agents": {
    "criacao_epicos_azure_devops": {
      "agent_name": "Epicos Azure DevOps",
      "mcp_url": "https://mcp-epicos.azurewebsites.net",
      "report_fields": ["epicos_report"]
    },
    "features_generation": {
      "agent_name": "Features Generator",
      "mcp_url": "https://mcp-features.azurewebsites.net",
      "report_fields": ["features_report"]
    }
  }
}

---

## Observações

- O campo `analysis_name` foi removido de todos os fluxos e payloads.
- Para iniciar análise, é obrigatório informar `analysis_type` e pelo menos um de `arquivo_docx` (texto extraído) ou `comentario_usuario`.
- O upload de DOCX processa upload e extração de texto em paralelo, retornando ambos imediatamente.
- O salvamento de estado no Blob Storage é automático e periódico, disparado por alterações de relatório ou estado.
- O cache de segredos do Key Vault é thread-safe e evita múltiplas chamadas desnecessárias.
- O Redis **deve** ser configurado via Key Vault (não via variáveis de ambiente do App Service).
- Para ambientes com Redis em subrede privada, o App Service deve estar integrado à mesma VNET.
- O sistema pode operar em modo de teste com autenticação mockada (`SKIP_AUTH_FOR_TESTING`), útil para desenvolvimento local.
- Todos os exemplos de payload e resposta estão detalhados em `backend/docs/API_PAYLOAD_EXAMPLES.md`.
- Toda a comunicação com o MCP utiliza o project_id como identificador principal. O job_id é apenas um identificador da execução no MCP, mas não é usado para buscar sessões no backend.
- Todos os relatórios são salvos em campos individuais (`epicos_report`, `features_report`, etc). Não existe mais a chave `reports` no estado do projeto ou sessão.
- O backend aceita o campo "projeto" (nome do projeto) do frontend, converte internamente para project_id, e responde sempre com ambos.
