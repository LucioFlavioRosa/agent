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
    AD -->|Busca Estado Resumo| AE
    AA -->|Inicia Análise (com arquivo docx)| AE
    AE -->|Extrai Texto| AA
    AE -->|Salva arquivo no Blob| AA
    AA -->|Cria Estado Resumo| AD
    AA -->|Envia para MCP| AF
    AF -->|Job ID| AA
    AF -->|Webhooks Progresso/Conclusão| AA
    AA -->|Atualiza Estado Individual do Report| AD
    AD -->|Salva Estado Individual| AE
    AG -->|Salvamento Periódico| AE
    AC -->|Carrega Segredos| AA

---

## Estrutura de Pastas no Blob Storage

mermaid
flowchart TD
    root[Blob Storage]
    subgraph usuario_executor
        projeto[projeto]
        subgraph estados
            resumo[resumo/]
            epicos[epicos/]
            features[features/]
            times[Times Descricao/]
            alocacao[Alocacao Times/]
            premissas[Premissas Riscos/]
        end
    end
    root --> usuario_executor
    usuario_executor --> projeto
    projeto --> estados
    estados --> resumo
    estados --> epicos
    estados --> features
    estados --> times
    estados --> alocacao
    estados --> premissas

    resumo --> estado_resumo_json[estado_resumo_*.json]
    epicos --> estado_epicos_json[estado_epicos_report_*.json]
    features --> estado_features_json[estado_features_report_*.json]
    times --> estado_times_json[estado_times_descricao_report_*.json]
    alocacao --> estado_alocacao_json[estado_alocacao_times_report_*.json]
    premissas --> estado_premissas_json[estado_premissas_riscos_report_*.json]

---

## Etapas do Fluxo e Código Responsável

### 1. Login e Autenticação via Azure AD
- O frontend envia o token JWT via header `Authorization`. O backend valida o token, extrai o `usuario_executor` e retorna a lista de projetos do usuário, contendo apenas o estado de resumo de cada projeto.
- Código:
  - `backend/app/api/auth.py` (`POST /auth/login`)
  - `backend/app/middleware/auth_middleware.py` (`get_current_user`)
  - `backend/app/services/azure_ad_service.py` (`validate_token`)
  - `backend/app/services/project_state_service.py` (`list_user_projects`)

### 2. Verificação de Projeto Existente
- O frontend chama `/projects/check` enviando o campo `nome_projeto`. O backend converte internamente para `project_id` usando o método auxiliar, e retorna o estado completo do projeto, incluindo todos os estados salvos (resumo + reports).
- Código:
  - `backend/app/api/projects.py` (`/projects/check`)
  - `backend/app/services/project_state_service.py` (`_get_project_id_by_name`, `load_all_states_from_blob`)

### 3. Início de Análise com Upload de DOCX
- O frontend chama `/analysis/start` enviando os campos `nome_projeto`, `analysis_type`, `instrucoes_extras` e opcionalmente `arquivo_docx` como arquivo via multipart/form-data.
- O backend extrai o texto do arquivo DOCX e salva o arquivo no Blob Storage em paralelo.
- O texto extraído é enviado ao MCP no campo `arquivo_docx` do payload.
- Código:
  - `backend/app/api/analysis.py` (`POST /analysis/start`)
  - `backend/app/services/blob_storage_service.py` (`upload_docx_to_blob`)
  - `backend/app/services/docx_parser_service.py` (`extract_text_from_docx`)

### 4. Criação e Gerenciamento de Estado Resumo e Estados Individuais de Report no Redis e Blob Storage
- O backend cria e persiste o estado de resumo do projeto no Redis e Blob Storage. Estados individuais de report são criados e atualizados conforme o tipo de análise executada. Cada tipo de estado é salvo em sua pasta específica no Blob Storage.
- Código:
  - `backend/app/services/redis_session_service.py` (`create_session`, `create_report_state`, `update_report_state`, `get_report_state`)
  - `backend/app/models/project_state_models.py` (`EstadoResumoProjeto`, `EstadoEpicos`, `EstadoFeatures`, `EstadoTimesDescricao`, `EstadoAlocacaoTimes`, `EstadoPremissasRiscos`, `EstadoCompletoProjetoResponse`)

### 5. Salvamento Automático e Periódico de Estado no Blob Storage
- Estados de resumo e de report são salvos periodicamente no Blob Storage via `BackgroundStateSaver`. Mudanças em relatórios ou estado acionam o salvamento automático. Cada tipo de estado é salvo em sua respectiva pasta.
- Código:
  - `backend/app/services/background_state_saver.py` (`schedule_periodic_save`)
  - `backend/app/services/project_state_service.py` (`save_state_to_blob`)

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
- O backend envia payloads para o MCP sempre usando `project_id` como identificador principal. O MCP responde com `job_id` e envia webhooks de progresso/conclusão, que atualizam estados individuais de report no Redis e Blob Storage.
- O campo `report_data` do webhook do MCP deve ser um dicionário com exatamente uma chave, que pode ser: `epicos_report`, `features_report`, `times_descricao_report`, `alocacao_times_report`, ou `premissas_riscos_report`. O backend atualiza diretamente o estado individual correspondente, sem sobrescrever outros relatórios. Cada tipo de report é salvo em sua pasta específica.
- Código:
  - `backend/app/services/mcp_client_service.py` (`start_analysis`)
  - `backend/app/services/redis_session_service.py` (`get_report_state`, `update_report_state`)
  - `backend/app/api/webhooks.py` (usa o mapping para atualizar o estado individual)

### 9. Consulta de Estado Individual de Report
- Estados individuais de report podem ser consultados pelo endpoint dedicado, retornando apenas os campos do report solicitado.
- Código:
  - `backend/app/api/session.py` (`GET /session/project/{project_id}/report/{report_type}`)
  - `backend/app/services/project_state_service.py` (`get_report_state`)

### 10. Consulta de Estado Completo do Projeto
- O backend retorna todos os estados salvos (resumo + reports) para o projeto, lendo sempre o arquivo mais recente de cada pasta. Se algum estado não existir, retorna o campo como `None` ou lista vazia conforme o modelo.
- Código:
  - `backend/app/api/projects.py` (`GET /projects/check`)
  - `backend/app/api/session.py` (`GET /session/project/{project_id}/reports`)
  - `backend/app/services/project_state_service.py` (`load_all_states_from_blob`)

---

## Observações

- O backend mantém um estado de resumo do projeto e estados individuais para cada report, cada um salvo em sua pasta específica no Blob Storage.
- O campo `ultima_analysis_type` indica qual foi a última análise executada no projeto ou report.
- O backend atualiza apenas o estado do report correspondente ao `analysis_type` recebido no webhook.
- O frontend deve fazer polling periódico para consultar estados de reports enquanto o MCP processa a análise.
- Para obter o estado completo do projeto, utilize o endpoint `GET /session/project/{project_id}/reports` ou `GET /projects/check`.
- O backend sempre retorna o estado mais atual de cada pasta.
