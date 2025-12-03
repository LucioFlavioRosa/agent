# Resumo Executivo

Este documento detalha o fluxo completo do backend Peers CodeAI, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integrações com Azure Key Vault, Blob Storage, Redis e MCP Server. Cada etapa está explicada, com referência ao arquivo de código responsável e um diagrama ilustrativo em Mermaid.

---

## Diagrama do Fluxo (Mermaid)

```mermaid
flowchart TD
    Z[Frontend] -->|0. Login| AA(API Layer)
    AA -->|1. Validação do Token| AB[Auth Middleware]
    AB -->|2. Busca Projetos do Usuário| AC[ProjectStateService]
    AC -->|3. Busca Estado no Blob Storage| AD[Blob Storage]
    AD -->|4. Lista de Projetos| AA
    AA -->|5. Resposta para Frontend| Z
    Z -->|6. Seleção de Projeto| B(API Layer)
    B -->|7. Verificação de Projeto Existente| C[ProjectStateService]
    C -->|8. Busca Estado no Blob Storage| D[Blob Storage]
    D -->|9. Resposta Estado| B
    B -->|10. Resposta para Frontend| Z
    Z -->|11. Iniciar Análise| B
    B -->|"12. Processamento DOCX (se enviado)"| E[Docx Parser Service]
    E -->|13. Salvamento DOCX| F[Blob Storage Service]
    B -->|14. Salvamento Sessão| G[Redis Session Service]
    G -->|15. Salvamento caminho do DOCX| G
    B -->|16. Leitura Variáveis Ambiente| H[Config Loader Service]
    H -->|17. Carregamento Segredos| I[Azure Key Vault]
    G -->|18. Salvamento Estado| F
    B -->|19. Busca Metadados Projeto| F
    B -->|20. Envio para MCP| J[MCP Server]
    J -->|21. Resposta MCP| B
    B -->|22. Resposta para Frontend| Z
    J -->|23. Resposta MCP → Backend| B
    B -->|24. Resposta Backend → Frontend| Z
```

> **Observação:** Os exemplos de payload de cada etapa (incluindo MCP → Backend e Backend → Frontend) estão documentados em detalhes em `backend/docs/API_PAYLOAD_EXAMPLES.md`.

---

## Etapa 0: Login e Listagem de Projetos
- **Descrição:** Após o login no frontend, o backend recebe o token via header `Authorization`, valida via Azure AD e busca todos os projetos do usuário no Blob Storage. A resposta inclui as informações do usuário autenticado e a lista de projetos encontrados, cada um com seu `project_id` único.
- **Código responsável:**
  - `backend/app/api/auth.py` (endpoint `POST /auth/login`)
  - `backend/app/middleware/auth_middleware.py` (função `get_current_user`)
  - `backend/app/services/project_state_service.py` (função `list_user_projects`)

---

## Etapas do Fluxo e Código Responsável

### 1. Seleção de Projeto e Verificação de Existência
- **Descrição:** Antes de qualquer operação (upload, análise), o frontend deve chamar o endpoint `/projects/check` para verificar se o projeto existe para o usuário autenticado. Se existir, o backend retorna o último estado salvo do projeto, incluindo o `project_id`.
- **Código responsável:**
  - `backend/app/api/projects.py` (endpoint `/projects/check`)
  - `backend/app/services/project_state_service.py` (função `load_latest_state_from_blob`)

### 2. Recebimento da Requisição do Frontend
- **Descrição:** O frontend envia requisições para o backend via endpoints HTTP para iniciar análise. O campo opcional `comentario_usuario` pode ser enviado junto com o arquivo DOCX ou na solicitação de análise.
- **Código responsável:**
  - `backend/app/api/analysis.py` (função `start_analysis`)

### 3. Processamento do DOCX (se enviado)
- **Descrição:** Se o campo `arquivo_docx` for enviado, o arquivo DOCX é processado para extrair o texto. O upload e a extração de texto agora ocorrem em paralelo, retornando tanto a URL do arquivo quanto o texto extraído.
- **Código responsável:**
  - `backend/app/services/docx_parser_service.py` (função `extract_text_from_docx`)
  - `backend/app/services/blob_storage_service.py` (função `upload_and_extract_docx`)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py` e em `backend/app/api/upload.py`

### 4. Salvamento do DOCX
- **Descrição:** O arquivo DOCX é salvo no Azure Blob Storage na pasta do usuário/projeto.
- **Código responsável:**
  - `backend/app/services/blob_storage_service.py` (função `upload_docx_to_blob` e `upload_and_extract_docx`)

### 5. Salvamento dos Dados no Redis
- **Descrição:** Sessões e relatórios são persistidos no Redis para rastreamento do estado. O campo opcional `comentario_usuario` é armazenado na sessão Redis. O texto extraído do DOCX é armazenado no campo `extracted_text` da sessão Redis.
- **Código responsável:**
  - `backend/app/services/redis_session_service.py` (funções `create_session`, `update_report`, `add_step`, `restore_session_from_state`, `get_session`, `add_docx_file`, `update_session_extracted_text`, `update_session_on_state_change`)
  - Campo `comentario_usuario` e `extracted_text` em `SessionData` (`backend/app/models/session_models.py`)

### 6. Salvamento do caminho do DOCX no estado da sessão
- **Descrição:** Todo arquivo DOCX enviado tem seu caminho salvo no campo `docx_files` do estado da sessão, garantindo histórico completo dos arquivos utilizados para geração e recuperação de todas as histórias.
- **Código responsável:**
  - `backend/app/services/redis_session_service.py` (função `add_docx_file`)
  - `backend/app/models/session_models.py` (campo `docx_files` em `SessionData`)
  - Chamado em `start_analysis` e durante restauração de sessão

### 7. Validação de Tokens
- **Descrição:** O token JWT do Azure AD é validado para autenticação e autorização do usuário.
- **Código responsável:**
  - `backend/app/middleware/auth_middleware.py` (função `get_current_user`)
  - `backend/app/services/azure_ad_service.py` (função `validate_token`)

### 8. Leitura das Variáveis de Ambiente
- **Descrição:** Variáveis de ambiente são lidas para configuração inicial do backend.
- **Código responsável:**
  - `backend/app/core/config.py` (classe `Settings`)
  - `startup.py` (função `validate_env_vars`)
  - `backend/app/services/config_loader_service.py` (classe `ConfigLoaderService`)

### 9. Key Vault
- **Descrição:** Segredos sensíveis são carregados do Azure Key Vault usando Managed Identity.
- **Código responsável:**
  - `backend/app/services/azure_secret_manager.py` (classe `AzureSecretManager`)
  - `backend/app/services/config_loader_service.py` (classe `ConfigLoaderService`, método `load_secrets_from_key_vault`)

### 10. Salvamento do Status no Blob Storage
- **Descrição:** O estado da sessão/projeto é salvo periodicamente no Blob Storage. Sempre que houver mudanças em relatórios ou variáveis de estado, o salvamento é acionado automaticamente.
- **Código responsável:**
  - `backend/app/services/project_state_service.py` (função `save_state_to_blob`)
  - `backend/app/services/background_state_saver.py` (classe `BackgroundStateSaver`, método `schedule_periodic_save`)
  - `backend/app/services/redis_session_service.py` (função `update_session_on_state_change`)
  - `backend/app/api/session.py` (endpoint PUT `/session/{session_id}/report`)

### 11. Verificação de Projeto Existente no Blob Storage
- **Descrição:** Antes de exigir o upload do DOCX, o backend verifica se já existe um estado do projeto para o usuário no Blob Storage. Se existir, o upload não é obrigatório. Se não existir, o upload do DOCX é obrigatório para criar o projeto.
- **Código responsável:**
  - `backend/app/services/project_state_service.py` (função `load_latest_state_from_blob`)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py`

### 12. Envio para o MCP Server
- **Descrição:** O backend envia para o MCP um dos três formatos de payload, conforme o recebido do frontend:
  - Com `arquivo_docx` e `comentario_usuario`
  - Apenas com `arquivo_docx`
  - Apenas com `comentario_usuario`
  O campo `analysis_name` NÃO é enviado. O campo `arquivo_docx` sempre contém o texto extraído do DOCX, nunca a URL do arquivo.
- **Código responsável:**
  - `backend/app/services/mcp_client_service.py` (função `start_analysis`)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py`

### 13. Recebimento da Resposta do MCP Server (MCP → Backend)
- **Descrição:** A resposta do MCP Server é processada e o job_id é extraído. Notificações de progresso, relatórios parciais e status de conclusão são recebidos e processados pelo backend.
- **Código responsável:**
  - `backend/app/services/mcp_client_service.py` (função `start_analysis` - retorno)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py`
- **Exemplos de payload:** Veja `backend/docs/API_PAYLOAD_EXAMPLES.md`, seção "Exemplos de Respostas MCP → Backend".

### 14. Envio da Resposta para o Frontend (Backend → Frontend)
- **Descrição:** A resposta final (incluindo URLs, job_id, mensagens, dados de sessão e `project_id`) é enviada para o frontend. O backend propaga erros do MCP para o frontend quando necessário.
- **Código responsável:**
  - `backend/app/api/analysis.py`, `backend/app/api/upload.py`, `backend/app/api/session.py`, `backend/app/api/auth.py` (retorno das funções FastAPI)
- **Exemplos de payload:** Veja `backend/docs/API_PAYLOAD_EXAMPLES.md`, seção "Exemplos de Respostas Backend → Frontend".

### 15. Recebimento do comentario_usuario do frontend
- **Descrição:** O campo opcional `comentario_usuario` é recebido do frontend nos endpoints de análise.
- **Código responsável:**
  - `backend/app/api/analysis.py` (função `start_analysis`)

### 16. Armazenamento do comentario_usuario na sessão Redis
- **Descrição:** O campo opcional `comentario_usuario` é persistido na sessão Redis para uso posterior.
- **Código responsável:**
  - `backend/app/services/redis_session_service.py` (função `create_session`, campo em SessionData)

### 17. Armazenamento do texto extraído do DOCX na sessão Redis
- **Descrição:** O texto extraído do DOCX é armazenado na sessão Redis durante o upload do arquivo. O upload e a extração de texto ocorrem em paralelo.
- **Código responsável:**
  - `backend/app/services/blob_storage_service.py` (função `upload_and_extract_docx`)
  - `backend/app/services/redis_session_service.py` (função `update_session_extracted_text`)
  - Chamado dentro de `backend/app/api/upload.py` após upload do DOCX

### 18. Envio do texto extraído para MCP Server
- **Descrição:** O campo `arquivo_docx` enviado para o MCP Server sempre contém o texto extraído do DOCX, nunca a URL do arquivo.
- **Código responsável:**
  - `backend/app/services/mcp_client_service.py` (função `start_analysis`)
  - Chamado dentro de `backend/app/api/analysis.py`

---

## Observações
- O campo `analysis_name` foi removido de todos os fluxos e payloads.
- O backend aceita apenas três formatos de payload para iniciar análise, conforme descrito em `API_PAYLOAD_EXAMPLES.md`.
- O backend sempre envia para o MCP um dos três formatos de payload, sem `analysis_name`.
- Todo arquivo DOCX enviado tem seu caminho salvo no estado da sessão, permitindo rastreabilidade e recuperação de todas as histórias geradas.
- O texto extraído do DOCX é armazenado na sessão Redis e enviado ao MCP.
- O upload de DOCX agora retorna tanto a URL do arquivo quanto o texto extraído, em paralelo.
- O fluxo garante flexibilidade para o frontend iniciar análises em projetos já existentes sem exigir novo upload ou campos extras, e permite o envio de comentários adicionais pelo usuário.
- Exemplos completos de payload de resposta do MCP para o backend e do backend para o frontend estão detalhados em `backend/docs/API_PAYLOAD_EXAMPLES.md`.
