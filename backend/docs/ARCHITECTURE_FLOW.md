# Resumo Executivo

Este documento detalha o fluxo completo do backend Peers CodeAI, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integrações com Azure Key Vault, Blob Storage, Redis e MCP Server. Cada etapa está explicada, com referência ao arquivo de código responsável e um diagrama ilustrativo em Mermaid.

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
    B -->|9. Verificação Projeto Existente| E
    B -->|10. Envio para MCP| I[MCP Server]
    I -->|11. Resposta MCP| B
    B -->|12. Resposta para Frontend| A
    A -->|13. Seleção Projeto Existente| B
    B -->|Busca Estado Projeto| E


---

## Etapas do Fluxo e Código Responsável

### 1. Recebimento da Requisição do Frontend
- **Descrição:** O frontend envia requisições para o backend via endpoints HTTP (upload de DOCX, iniciar análise, salvar estado, etc).
- **Código responsável:**
  - `backend/app/api/upload.py` (função `upload_docx`)
  - `backend/app/api/analysis.py` (função `start_analysis`)
  - `backend/app/api/session.py` (funções `get_session_reports`, `update_session_report`, `save_session_state`)
  - `backend/app/api/auth.py` (função `get_auth_config`)

### 2. Processamento do DOCX
- **Descrição:** O arquivo DOCX enviado pelo frontend é processado para extrair o texto.
- **Código responsável:**
  - `backend/app/services/docx_parser_service.py` (função `extract_text_from_docx`)
  - Chamado dentro de `upload_docx` em `backend/app/api/upload.py`

### 3. Salvamento do DOCX
- **Descrição:** O arquivo DOCX é salvo no Azure Blob Storage na pasta do usuário/projeto.
- **Código responsável:**
  - `backend/app/services/blob_storage_service.py` (função `upload_docx_to_blob`)
  - Chamado dentro de `upload_docx` em `backend/app/api/upload.py`

### 4. Salvamento dos Dados no Redis
- **Descrição:** Sessões e relatórios são persistidos no Redis para rastreamento do estado.
- **Código responsável:**
  - `backend/app/services/redis_session_service.py` (funções `create_session`, `update_report`, `add_step`, `restore_session_from_state`, `get_session`)
  - Chamado em endpoints de análise e sessão

### 5. Validação de Tokens
- **Descrição:** O token JWT do Azure AD é validado para autenticação e autorização do usuário.
- **Código responsável:**
  - `backend/app/middleware/auth_middleware.py` (função `get_current_user`)
  - `backend/app/services/azure_ad_service.py` (função `validate_token`)

### 6. Leitura das Variáveis de Ambiente
- **Descrição:** Variáveis de ambiente são lidas para configuração inicial do backend.
- **Código responsável:**
  - `backend/app/core/config.py` (classe `Settings`)
  - `startup.py` (função `validate_env_vars`)
  - `backend/app/services/config_loader_service.py` (classe `ConfigLoaderService`)

### 7. Key Vault
- **Descrição:** Segredos sensíveis são carregados do Azure Key Vault usando Managed Identity.
- **Código responsável:**
  - `backend/app/services/azure_secret_manager.py` (classe `AzureSecretManager`)
  - `backend/app/services/config_loader_service.py` (classe `ConfigLoaderService`, método `load_secrets_from_key_vault`)

### 8. Salvamento do Status no Blob Storage
- **Descrição:** O estado da sessão/projeto é salvo periodicamente no Blob Storage.
- **Código responsável:**
  - `backend/app/services/project_state_service.py` (função `save_state_to_blob`)
  - `backend/app/services/background_state_saver.py` (classe `BackgroundStateSaver`, método `schedule_periodic_save`)

### 9. Verificação de Projeto Existente no Blob Storage
- **Descrição:** Antes de exigir o upload do DOCX, o backend verifica se já existe um estado do projeto para o usuário no Blob Storage. Se existir, o upload não é obrigatório. Se não existir, o upload do DOCX é obrigatório para criar o projeto.
- **Código responsável:**
  - `backend/app/services/project_state_service.py` (função `load_latest_state_from_blob`)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py`

### 10. Envio para o MCP Server
- **Descrição:** Payload de análise é enviado para o MCP Server via HTTP.
- **Código responsável:**
  - `backend/app/services/mcp_client_service.py` (função `start_analysis`)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py`

### 11. Recebimento da Resposta do MCP Server
- **Descrição:** A resposta do MCP Server é processada e o job_id é extraído.
- **Código responsável:**
  - `backend/app/services/mcp_client_service.py` (função `start_analysis` - retorno)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py`

### 12. Envio para o Frontend
- **Descrição:** A resposta final (incluindo URLs, job_id, mensagens e dados de sessão) é enviada para o frontend.
- **Código responsável:**
  - `backend/app/api/analysis.py`, `backend/app/api/upload.py`, `backend/app/api/session.py`, `backend/app/api/auth.py` (retorno das funções FastAPI)

### 13. Busca do Estado do Projeto no Blob Storage (Projeto Existente)
- **Descrição:** Quando o usuário seleciona um projeto existente, o estado é recuperado do Blob Storage e restaurado na sessão Redis.
- **Código responsável:**
  - `backend/app/services/project_state_service.py` (função `load_latest_state_from_blob`)
  - Chamado dentro de `start_analysis` em `backend/app/api/analysis.py` quando detectado projeto existente

---

## Fluxo Resumido

1. O frontend faz uma requisição (ex: upload de DOCX ou iniciar análise).
2. O backend valida o token do usuário (Azure AD).
3. O backend verifica se o projeto já existe para o usuário no Blob Storage.
4. Se o projeto não existir, o upload do DOCX é obrigatório para criar o projeto.
5. Se o projeto existir, o upload do DOCX é opcional e pode ser omitido.
6. O arquivo DOCX (se enviado) é processado e o texto extraído.
7. O arquivo é salvo no Azure Blob Storage.
8. Uma sessão é criada ou restaurada no Redis, persistindo dados relevantes.
9. Variáveis de ambiente e segredos do Key Vault são carregados para configuração.
10. O estado do projeto/sessão é salvo periodicamente no Blob Storage.
11. O estado pode ser lido do Blob Storage para restaurar sessões.
12. O payload de análise é enviado para o MCP Server.
13. A resposta do MCP Server é recebida e processada.
14. O backend envia a resposta final para o frontend.
15. Quando o usuário seleciona um projeto existente, o estado é buscado no Blob Storage e restaurado.

---

## Observações
- O backend só exige o upload do DOCX se o projeto não existir previamente para o usuário.
- O diagrama Mermaid foi atualizado para incluir a etapa de verificação de projeto existente no Blob Storage antes do processamento do DOCX.
- O fluxo garante flexibilidade para o frontend iniciar análises em projetos já existentes sem exigir novo upload.
