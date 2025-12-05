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
    AA -->|"Início de Análise (inclui upload DOCX)"| AE
    AE -->|Extrai Texto| AA
    AA -->|Cria Sessão| AD
    AA -->|"Envia para MCP (sempre com session_id)"| AF
    AF -->|session_id| AA
    AF -->|"Webhooks Progresso/Conclusão (session_id)"| AA
    AA -->|Atualiza Relatórios| AD
    AD -->|Salva Estado| AE
    AG -->|Salvamento Periódico| AE
    AC -->|Carrega Segredos| AA
    %% Recuperação automática de sessão do Blob Storage
    AA -->|Recupera Sessão do Blob se não encontrada no Redis| AE
    AE -->|Restaura Sessão no Redis| AD
    %% Salvamento imediato após atualização de relatório
    AA -->|Salva Estado Imediatamente após Webhook MCP| AE


---

## Etapas do Fluxo e Código Responsável

### 1. Login e Autenticação via Azure AD
- O frontend envia o token JWT via header `Authorization`. O backend valida o token, extrai o `usuario_executor` e retorna a lista de projetos do usuário.
- O backend gera um novo `session_id` apenas se não houver nenhum projeto existente para o usuário. Caso contrário, o `session_id` retornado é sempre o mesmo do estado mais recente do projeto selecionado (extraído do Redis ou Blob Storage, nunca gerado novamente para projetos existentes).
- O `session_id` é o único identificador propagado em todas as interações da sessão.
- Código:
  - `backend/app/api/auth.py` (`POST /auth/login`)
  - `backend/app/middleware/auth_middleware.py` (`get_current_user`)
  - `backend/app/services/azure_ad_service.py` (`validate_token`)
  - `backend/app/services/project_state_service.py` (`list_user_projects`, `get_session_id_from_latest_state`)

### 2. Verificação de Projeto Existente
- O frontend chama `/projects/check` para saber se o projeto existe. O backend busca o estado mais recente do projeto **primeiro no Redis** (sessão ativa), e só faz fallback para o Blob Storage se não encontrar no Redis.
- O estado retornado sempre inclui o `session_id` da sessão mais recente (do Redis ou Blob).
- Se a sessão não estiver no Redis, o backend restaura a sessão usando o `session_id` do Blob antes de retornar o estado.
- Código:
  - `backend/app/api/projects.py` (`/projects/check`)
  - `backend/app/services/redis_session_service.py` (`get_session_by_project`, `restore_session_from_state`)
  - `backend/app/services/project_state_service.py` (`load_latest_state_from_redis`, `load_latest_state_from_blob`, `get_session_id_from_latest_state`)

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
        BE->>RS: restore_session_from_state(usuario_executor, projeto, analysis_type, state, session_id)
        RS-->>BE: session_id
        BE-->>FE: exists: true, state (do Blob Storage)
    end
    Note over BE: O campo 'reports' sempre reflete o estado mais recente disponível


### 3. Início de Análise e Upload de DOCX (Processamento Paralelo)
- O upload do arquivo DOCX e a extração do texto ocorrem dentro do endpoint `/analysis/start` via multipart/form-data. O backend retorna tanto a URL do arquivo quanto o texto extraído.
- O backend sempre envia o `session_id` para o MCP e espera que o MCP retorne o mesmo `session_id` em todas as respostas e webhooks.
- Para projetos existentes, o `session_id` é sempre reutilizado do estado mais recente.
- Código:
  - `backend/app/api/analysis.py` (`/analysis/start`)
  - `backend/app/services/blob_storage_service.py` (`upload_and_extract_docx`)
  - `backend/app/services/docx_parser_service.py` (`extract_text_from_docx`)

### 4. Criação e Gerenciamento de Sessão no Redis
- Sessões são criadas e persistidas no Redis, incluindo campos como `comentario_usuario`, `extracted_text`, `project_id`, `docx_files` e `reports`.
- O único identificador de sessão é o `session_id`, gerado no login (apenas para projetos novos) ou sempre reutilizado para projetos existentes.
- Na restauração de sessão a partir do estado do Blob, o `session_id` passado sempre deve ser igual ao do estado carregado. Se forem diferentes, um aviso é logado e o `session_id` do estado é utilizado.
- Código:
  - `backend/app/services/redis_session_service.py` (`create_session`, `add_docx_file`, `update_session_extracted_text`, `update_report`, `restore_session_from_state`, `get_session_by_project`)
  - `backend/app/models/session_models.py` (`SessionData`)

### 5. Salvamento Automático e Periódico de Estado no Blob Storage
- Estados de sessão/projeto são salvos periodicamente no Blob Storage via `BackgroundStateSaver`. Mudanças em relatórios ou estado acionam o salvamento automático.
- Cada novo estado é salvo como um novo arquivo, nunca sobrescrevendo o anterior. O nome do arquivo sempre inclui o `session_id` e um timestamp.
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

## 8. Webhook MCP: Recuperação Automática de Sessão e Atualização de Relatório

A partir da versão X.X.X, o backend garante que **toda vez que um webhook do MCP é recebido, o relatório é atualizado corretamente**, mesmo que a sessão não esteja mais presente no Redis (por exemplo, após expiração, reinício ou falha do Redis). O fluxo é o seguinte:

### Diagrama de Sequência: Webhook MCP → Recuperação de Sessão → Atualização de Relatório

mermaid
sequenceDiagram
    participant MCP as MCP Server
    participant BE as Backend
    participant RS as RedisSessionService
    participant PS as ProjectStateService
    participant BS as Blob Storage
    MCP->>BE: POST /webhooks/mcp (session_id, status, report_type, ...)
    BE->>RS: get_session(session_id)
    alt Sessão encontrada no Redis
        RS-->>BE: SessionData
        BE->>RS: update_report(session_id, ...)
        RS-->>BE: OK
    else Sessão NÃO encontrada no Redis
        BE->>PS: load_latest_state_from_blob(usuario_executor, projeto, session_id)
        alt Encontrou estado no Blob
            PS-->>BE: project_state
            BE->>RS: restore_session_from_state(usuario_executor, projeto, analysis_type, project_state, session_id)
            RS-->>BE: session_id
            BE->>RS: update_report(session_id, ...)
            RS-->>BE: OK
        else Não encontrou estado no Blob
            BE->>PS: load_latest_state_by_session_id(session_id)
            alt Encontrou estado pelo session_id
                PS-->>BE: project_state
                BE->>RS: restore_session_from_state(usuario_executor, projeto, analysis_type, project_state, session_id)
                RS-->>BE: session_id
                BE->>RS: update_report(session_id, ...)
                RS-->>BE: OK
            else Não encontrou estado em lugar nenhum
                BE-->>MCP: 404 Sessão não encontrada
            end
        end
    end
    Note over BE: O relatório é sempre atualizado, não importa se a sessão foi criada em outra sessão ou restaurada do Blob


### Código Responsável
- `backend/app/api/webhooks.py` (endpoint `/webhooks/mcp`):
  - Tenta buscar a sessão no Redis. Se não encontrar, busca no Blob Storage usando `usuario_executor` e `projeto` (se disponíveis) ou apenas `session_id`.
  - Se encontrar o estado, restaura a sessão no Redis e executa a atualização do relatório.
  - Se não encontrar em nenhum lugar, retorna 404.
  - Logs detalhados em cada etapa.
- `backend/app/services/redis_session_service.py`:
  - Função `_ensure_session_exists` implementa toda a lógica de busca e restauração automática.
  - Função `update_report` sempre chama `_ensure_session_exists` antes de atualizar o relatório.
  - Função `restore_session_from_state` garante que o session_id passado seja igual ao do estado carregado, logando um aviso se forem diferentes.
- `backend/app/services/project_state_service.py`:
  - Função `load_latest_state_by_session_id` permite buscar o estado no Blob Storage apenas pelo `session_id`.

### Garantias do Novo Fluxo
- O relatório é atualizado sempre que um webhook do MCP é recebido, independentemente do estado do Redis.
- O frontend pode confiar que, ao consultar `/projects/check`, o estado refletirá o relatório mais recente, mesmo após falhas temporárias do Redis.
- Logs detalhados permitem rastrear todo o fluxo de recuperação e atualização.

---

## 9. Salvamento Imediato de Estado

Após cada atualização de relatório via webhook MCP (ou via endpoint manual), o backend salva imediatamente o estado atualizado no Blob Storage. Isso garante consistência e minimiza perda de dados em caso de falha.

- O estado é sempre salvo como um novo arquivo, nunca sobrescrevendo o anterior.
- O nome do arquivo salvo sempre inclui o `session_id` e um timestamp.
- O backend nunca atualiza um registro de sessão já salvo: sempre cria um novo estado com os dados atualizados da sessão.
- Código:
  - `backend/app/services/project_state_service.py` (`save_state_to_blob`)
  - `backend/app/services/redis_session_service.py` (`update_report`)

---

## 10. Isolamento dos Relatórios: Atualização Independente dos Campos de Relatório

O backend Peers CodeAI garante que a atualização de qualquer campo de relatório (`epicos_report`, `features_report`, `times_descricao_report`, `alocacao_times_report`, `premissas_riscos_report`) é totalmente independente dos demais. Isso significa que ao atualizar, por exemplo, o `features_report`, todos os outros campos de relatório presentes no estado do projeto (Redis e Blob Storage) são preservados sem alteração.

### Como funciona o isolamento dos relatórios
- Cada campo de relatório é armazenado separadamente no estado do projeto e na sessão do Redis.
- A função `update_report` sempre carrega o estado completo da sessão antes de atualizar o campo solicitado, preservando todos os demais campos de relatório.
- Após a atualização de qualquer relatório, o backend salva o estado completo (com todos os campos) no Redis e no Blob Storage.
- Se algum campo de relatório estiver ausente após a atualização, o backend preenche com `None` e loga um aviso crítico.
- Isso garante que múltiplas atualizações de relatórios (em qualquer ordem) nunca sobrescrevem ou apagam relatórios anteriores.

### Diagrama de Sequência: Atualização Isolada de Relatórios

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant RS as RedisSessionService
    participant PS as ProjectStateService
    FE->>BE: POST /webhooks/mcp (session_id, report_type="features", report_data={...})
    BE->>RS: get_session(session_id)
    RS-->>BE: SessionData (contendo epicos_report, features_report, ...)
    BE->>RS: update_report(session_id, report_type="features", report_data={...})
    Note right of RS: Apenas features_report é atualizado<br/>Todos os outros campos são preservados
    RS-->>BE: OK
    BE->>PS: save_state_to_blob(SessionData)
    PS-->>BE: Blob salvo com todos os campos de relatório
    BE-->>FE: status: ok


### Garantias de Isolamento
- Atualizar `features_report` não afeta `epicos_report` ou qualquer outro campo.
- Atualizar `alocacao_times_report` não afeta `features_report` ou os demais.
- Todos os campos de relatório são sempre retornados no estado do projeto, mesmo que alguns estejam `null`.
- O frontend pode confiar que o backend nunca sobrescreve ou apaga relatórios existentes ao atualizar outro campo.

---

## Observações

- O campo `session_id` é o único identificador usado em toda a comunicação entre frontend, backend e MCP. Nunca é gerado novamente para projetos existentes.
- O backend sempre prioriza o estado do Redis (sessão ativa). Se não encontrar, faz fallback para o Blob Storage e restaura a sessão antes de retornar o estado.
- O campo `reports` reflete imediatamente qualquer atualização feita via webhook do MCP ou via endpoint manual.
- Após cada atualização de relatório, o estado é salvo imediatamente no Blob Storage, criando um novo arquivo (nunca sobrescreve o anterior).
- O upload de DOCX ocorre dentro do endpoint `/analysis/start` via multipart/form-data, e o texto extraído é enviado ao MCP.
- Não há mais referências a `job_id` ou `analysis_name` em nenhum fluxo ou payload.
- O frontend pode confiar que a consulta ao endpoint `/projects/check` sempre retorna o estado mais atualizado possível, priorizando o Redis.
- O MCP nunca gera nenhum identificador próprio: sempre recebe e retorna o `session_id` enviado pelo backend.
- O backend nunca atualiza um registro de sessão já salvo: sempre cria um novo estado com os dados atualizados da sessão.
- A consistência e unicidade do `session_id` são garantidas em toda a comunicação e persistência de estado.
- Todos os caminhos de arquivo e funções mencionadas refletem a base de código atual.
