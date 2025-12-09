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

## 2. Criação de Projeto e Conversão nome_projeto → project_id

O frontend deve sempre enviar apenas o campo `nome_projeto` para criação ou início de análise. O backend é responsável por converter internamente o `nome_projeto` para `project_id`:
- Se o projeto já existe, o backend recupera o mesmo `project_id` do estado salvo.
- Se o projeto é novo, o backend gera um novo `project_id` (UUID) e associa ao nome do projeto.
- O `project_id` é retornado na resposta do backend para uso em operações subsequentes.

Diagrama de Fluxo Atualizado:

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant MCP as MCP Server
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, ...)
    BE->>BE: Converte nome_projeto para project_id (recupera existente ou gera novo)
    BE->>MCP: Envia payload (project_id, analysis_type, ...)
    MCP-->>BE: job_id, project_id
    BE-->>FE: message, project_id, nome_projeto

---

## 3. Consulta de Projeto Existente

mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (nome_projeto)
    BE->>BE: Busca project_id associado ao nome_projeto
    BE-->>FE: exists: true, state (inclui project_id)

---

## 4. Observações Importantes

- O campo `project_id` nunca deve ser enviado pelo frontend. O backend faz toda a conversão e retorna o `project_id` correto.
- Toda comunicação interna e com MCP utiliza o `project_id` gerado ou recuperado pelo backend.
- O frontend deve usar o `project_id` retornado para todas operações subsequentes (consultas, atualizações, etc).

---

# As demais seções permanecem inalteradas.
