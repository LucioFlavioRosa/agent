# Arquitetura e Fluxos do Backend Peers CodeAI

Este documento detalha o fluxo completo do backend Peers CodeAI, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integrações com Azure Key Vault (múltiplos cofres), Blob Storage, Redis, MCP Server e o mecanismo de configuração dinâmica de agentes. Cada etapa está explicada, com referência ao arquivo de código responsável e diagramas ilustrativos.

---

## 1. Login e Autenticação via Azure AD

Fluxo:
1. O frontend envia o token JWT via header Authorization para o endpoint POST /auth/login.
2. O backend valida o token via AzureADService, usando a chave pública do Azure AD (JWKS).
3. O backend extrai o usuario_executor dos claims do token (preferred_username, email ou upn).
4. O backend busca os projetos associados ao usuario_executor usando ProjectStateService._fetch_and_sanitize_projects.
5. O backend retorna para o frontend a lista de projetos de resumo, contendo apenas os campos: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, project_id.

Diagrama Mermaid:

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant AzureAD as Azure AD
    participant Blob as Blob Storage
    participant Redis as Redis
    FE->>BE: POST /auth/login (token JWT)
    BE->>AzureAD: Valida token JWT
    AzureAD-->>BE: Claims válidos
    BE->>BE: Extrai usuario_executor dos claims
    BE->>Blob: Busca projetos de resumo do usuario_executor
    BE->>Redis: Busca estados de resumo no cache
    BE-->>FE: Retorna user_info + lista de projetos de resumo

---

## Etapas do Fluxo e Código Responsável

### 1. Login e Autenticação via Azure AD
- O frontend envia o token JWT via header Authorization. O backend valida o token, extrai o usuario_executor e retorna a lista de projetos do usuário, contendo apenas o estado de resumo de cada projeto.
- Código:
  - `backend/app/api/auth.py` (`POST /auth/login`)
  - `backend/app/middleware/auth_middleware.py` (`get_current_user`)
  - `backend/app/services/azure_ad_service.py` (`validate_token`)
  - `backend/app/services/project_state_service.py` (`_fetch_and_sanitize_projects`)

---

# As demais seções permanecem inalteradas.
