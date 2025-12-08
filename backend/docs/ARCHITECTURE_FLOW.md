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
    AA -->|Inicia Análise (com arquivo docx)| AE
    AE -->|Extrai Texto| AA
    AE -->|Salva arquivo no Blob| AA
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
- O frontend chama `/projects/check` enviando o campo `nome_projeto`. O backend converte internamente para `project_id` usando o método auxiliar, e todas as operações subsequentes usam `project_id` como identificador principal.
- Código:
  - `backend/app/api/projects.py` (`/projects/check`)
  - `backend/app/services/project_state_service.py` (`_get_project_id_by_name`, `load_latest_state_from_blob`)

### 3. Início de Análise com Upload de DOCX
- O frontend chama `/analysis/start` enviando os campos `nome_projeto`, `analysis_type`, `instrucoes_extras` e opcionalmente `arquivo_docx` como arquivo via multipart/form-data.
- O backend extrai o texto do arquivo DOCX e salva o arquivo no Blob Storage em paralelo.
- O texto extraído é enviado ao MCP no campo `arquivo_docx` do payload.
- Código:
  - `backend/app/api/analysis.py` (`POST /analysis/start`)
  - `backend/app/services/blob_storage_service.py` (`upload_docx_to_blob`)
  - `backend/app/services/docx_parser_service.py` (`extract_text_from_docx`)

### 4. Criação e Gerenciamento de Sessão no Redis
- Sessões são criadas e persistidas no Redis, incluindo campos como `extracted_text`, `project_id`, `docx_files` e os campos de relatório individuais (`epicos_report`, `features_report`, etc).
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
- O campo `report_data` do webhook do MCP deve ser um dicionário com exatamente uma chave, que pode ser: `epicos_report`, `features_report`, `times_descricao_report`, `alocacao_times_report` ou `premissas_riscos_report`. O valor é sempre uma lista de itens do relatório. O backend atualiza diretamente o campo correspondente no estado do projeto/sessão, sem sobrescrever outros relatórios.
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

---

## Fluxos Críticos de Negócio

### 1. Fluxo de Novo Projeto (Criação de project_id)
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
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, instrucoes_extras, arquivo_docx)
    BE->>BE: Busca project_id pelo nome do projeto
    alt Projeto não existe
        BE->>BE: Cria novo project_id (uuid)
        BE->>RS: Cria sessão (com novo project_id)
    else Projeto já existe
        BE->>BE: Usa project_id existente
        BE->>RS: Restaura sessão do estado existente
    end
    BE->>BE: Extrai texto do arquivo docx
    par Processamento paralelo
        BE->>BS: Salva arquivo docx no Blob Storage
        BE->>BE: Extrai texto do arquivo docx
    end
    BE->>MCP: Envia payload (project_id, analysis_type, instrucoes_extras, texto extraído do arquivo docx)
    MCP-->>BE: job_id, project_id
    BE->>BS: Salva estado inicial
    BE-->>FE: job_id, project_id, nome_projeto

### 2. Fluxo de Projeto Existente (Reutilização de project_id)
mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (nome_projeto)
    BE->>BE: Busca project_id correspondente ao nome do projeto
    BE->>BS: Busca estado usando project_id
    BE-->>FE: exists: true, state (com campos de relatório individuais, project_id e nome_projeto)
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, instrucoes_extras, arquivo_docx)
    BE->>BE: Busca project_id correspondente ao nome do projeto
    BE->>RS: Restaura sessão do estado (com project_id e nome_projeto)
    BE->>BE: Extrai texto do arquivo docx
    par Processamento paralelo
        BE->>BS: Salva arquivo docx no Blob Storage
        BE->>BE: Extrai texto do arquivo docx
    end
    BE->>MCP: Envia payload (project_id, analysis_type, instrucoes_extras, texto extraído do arquivo docx)
    MCP-->>BE: job_id, project_id
    BE->>BS: Salva estado
    BE-->>FE: job_id, project_id, nome_projeto

### 3. Fluxo de Atualização de Relatório (Webhook MCP)
mermaid
sequenceDiagram
    MCP->>BE: Webhook (job_id, project_id, status, report_data)
    BE->>RS: Busca sessão por project_id (usando relação persistida project_id)
    BE->>RS: Atualiza relatório individual na sessão (ex: features_report)
    par Atualização paralela
        BE->>RS: Salva sessão atualizada no Redis
        BE->>BS: Salva estado atualizado no Blob Storage
    end

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

## Observações

- O endpoint /upload/docx foi removido. O upload de arquivo DOCX e a extração de texto ocorrem exclusivamente via POST /analysis/start.
- Para iniciar análise, é obrigatório informar `analysis_type` e pelo menos um de `arquivo_docx` (arquivo) ou `instrucoes_extras`.
- O upload de DOCX processa upload e extração de texto em paralelo, retornando ambos imediatamente.
- O salvamento de estado no Blob Storage é automático e periódico, disparado por alterações de relatório ou estado.
- O cache de segredos do Key Vault é thread-safe e evita múltiplas chamadas desnecessárias.
- O Redis deve ser configurado via Key Vault (não via variáveis de ambiente do App Service).
- Para ambientes com Redis em subrede privada, o App Service deve estar integrado à mesma VNET.
- Toda a comunicação com o MCP utiliza o project_id como identificador principal.
- Todos os relatórios são salvos em campos individuais (`epicos_report`, `features_report`, etc). Não existe mais a chave `reports` ou campos obsoletos no estado do projeto ou sessão.
- O backend aceita o campo "nome_projeto" do frontend, converte internamente para project_id, e responde sempre com ambos.
- O project_id é criado apenas quando o projeto é novo. Para projetos existentes, o project_id é lido do estado e mantido como referência única para todas as ações futuras relacionadas ao projeto.
- O ProjectStateService mantém um cache local do mapeamento nome_projeto → project_id, que é invalidado sempre que um novo estado é salvo no Blob Storage (ex: criação de projeto novo ou atualização de estado). Isso reduz chamadas desnecessárias ao Blob Storage e garante consistência do identificador.
