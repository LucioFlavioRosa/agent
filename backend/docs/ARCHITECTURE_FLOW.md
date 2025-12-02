# Resumo Executivo

Este documento descreve o fluxo completo da aplicação Peers CodeAI Backend, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integração com Azure Key Vault, Blob Storage, Redis e MCP Server. Cada etapa do processo está detalhada, com referência ao arquivo de código responsável e um diagrama ilustrativo em Mermaid.

---

## Diagrama do Fluxo (Mermaid)

mermaid
flowchart TD
    A[Frontend] -->|1. Requisição| B(API Layer)
    B -->|2. Validação de Token| C[Auth Middleware]
    B -->|3. Processamento DOCX| D[Docx Parser Service]
    D -->|4. Salvamento DOCX| E[Blob Storage Service]
    B -->|5. Salvamento Sessão| F[Redis Session Service]
    B -->|6. Leitura Variáveis Ambiente| G[Config Loader Service]
    G -->|7. Carregamento Segredos| H[Azure Key Vault]
    F -->|8. Salvamento Estado| E
    B -->|9. Leitura Estado| E
    B -->|10. Envio para MCP| I[MCP Server]
    I -->|11. Resposta MCP| B
    B -->|12. Resposta para Frontend| A
    A -->|13. Seleção Projeto Existente| B
    B -->|Busca Estado Projeto| E


---

## Etapas do Fluxo e Código Responsável

### 1. Recebimento da Requisição do Frontend
- **Arquivo:** `backend/app/api/upload.py`, `backend/app/api/analysis.py`, `backend/app/api/session.py`, `backend/app/api/auth.py`
- **Funções:**
  - Upload de DOCX: `upload_docx`
  - Iniciar análise: `start_analysis`
  - Sessão/relatórios: `get_session_reports`, `update_session_report`, `save_session_state`
  - Configuração de autenticação: `get_auth_config`

### 2. Processamento do DOCX
- **Arquivo:** `backend/app/services/docx_parser_service.py`
- **Função:** `extract_text_from_docx`
- O arquivo DOCX é lido e o texto extraído para uso posterior.

### 3. Salvamento do DOCX
- **Arquivo:** `backend/app/services/blob_storage_service.py`
- **Função:** `upload_docx_to_blob`
- O arquivo é salvo no Azure Blob Storage, na pasta do usuário/projeto.

### 4. Salvamento dos Dados no Redis
- **Arquivo:** `backend/app/services/redis_session_service.py`
- **Funções:** `create_session`, `update_report`, `add_step`, `restore_session_from_state`, `get_session`
- Sessões e relatórios são persistidos no Redis para rastreamento do estado.

### 5. Validação de Tokens
- **Arquivo:** `backend/app/middleware/auth_middleware.py`, `backend/app/services/azure_ad_service.py`
- **Funções:** `get_current_user`, `validate_token`
- O token JWT do Azure AD é validado para autenticação e autorização.

### 6. Leitura das Variáveis de Ambiente
- **Arquivo:** `backend/app/core/config.py`, `backend/app/services/config_loader_service.py`, `startup.py`
- **Funções:** `Settings`, `ConfigLoaderService.load_secrets_from_key_vault`, `validate_env_vars`
- Variáveis de ambiente são lidas para configuração inicial.

### 7. Key Vault
- **Arquivo:** `backend/app/services/azure_secret_manager.py`, `backend/app/services/config_loader_service.py`
- **Funções:** `AzureSecretManager.get_secret`, `ConfigLoaderService.load_secrets_from_key_vault`
- Segredos sensíveis são carregados do Azure Key Vault.

### 8. Salvamento do Status no Blob Storage
- **Arquivo:** `backend/app/services/project_state_service.py`, `backend/app/services/background_state_saver.py`
- **Funções:** `save_state_to_blob`, `BackgroundStateSaver.schedule_periodic_save`
- O estado da sessão/projeto é salvo periodicamente no Blob Storage.

### 9. Leitura de Status no Storage
- **Arquivo:** `backend/app/services/project_state_service.py`
- **Função:** `load_latest_state_from_blob`
- O estado mais recente do projeto/sessão é recuperado do Blob Storage.

### 10. Envio para o MCP Server
- **Arquivo:** `backend/app/services/mcp_client_service.py`
- **Função:** `start_analysis`
- Payload de análise é enviado para o MCP Server via HTTP.

### 11. Recebimento da Resposta do MCP Server
- **Arquivo:** `backend/app/services/mcp_client_service.py`
- **Função:** `start_analysis` (retorno)
- A resposta do MCP Server é processada e o job_id é extraído.

### 12. Envio para o Frontend
- **Arquivo:** `backend/app/api/analysis.py`, `backend/app/api/upload.py`, `backend/app/api/session.py`, `backend/app/api/auth.py`
- **Funções:** Retorno das funções FastAPI
- A resposta final é enviada para o frontend, incluindo URLs, job_id, mensagens e dados de sessão.

### 13. Busca do Estado do Projeto no Blob Storage (Projeto Existente)
- **Arquivo:** `backend/app/services/project_state_service.py`, `backend/app/api/analysis.py`
- **Funções:** `load_latest_state_from_blob`, chamada dentro de `start_analysis`
- Quando o usuário seleciona um projeto existente, o estado é recuperado do Blob Storage e restaurado na sessão Redis.

---

## Fluxo Resumido

1. O frontend faz uma requisição (ex: upload de DOCX ou iniciar análise).
2. O backend valida o token do usuário (Azure AD).
3. O arquivo DOCX é processado e o texto extraído.
4. O arquivo é salvo no Azure Blob Storage.
5. Uma sessão é criada ou restaurada no Redis, persistindo dados relevantes.
6. Variáveis de ambiente e segredos do Key Vault são carregados para configuração.
7. O estado do projeto/sessão é salvo periodicamente no Blob Storage.
8. O estado pode ser lido do Blob Storage para restaurar sessões.
9. O payload de análise é enviado para o MCP Server.
10. A resposta do MCP Server é recebida e processada.
11. O backend envia a resposta final para o frontend.
12. Quando o usuário seleciona um projeto existente, o estado é buscado no Blob Storage e restaurado.

---

## Observações
- Cada etapa do fluxo está fortemente acoplada a um ou mais arquivos de serviço, garantindo separação de responsabilidades e fácil manutenção.
- O diagrama Mermaid pode ser visualizado em ferramentas compatíveis para uma visão gráfica do fluxo.
