# Arquitetura e Fluxos do Backend Peers CodeAI

Este documento detalha o fluxo completo do backend Peers CodeAI, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integrações com Azure Key Vault (múltiplos cofres), Blob Storage, Redis, MCP Server e o mecanismo de configuração dinâmica de agentes. Cada etapa está explicada, com referência ao arquivo de código responsável e diagramas ilustrativos.

---

## Índice

1. Visão Geral da Comunicação entre Grandes Blocos
2. Login e Autenticação via Azure AD
3. Criação de Projeto e Conversão nome_projeto → project_id
4. Consulta de Projeto Existente
5. Observações Importantes
6. Enriquecimento de Contexto para Refinamento

---

## 1. Visão Geral da Comunicação entre Grandes Blocos

Esta seção apresenta uma visão de alto nível da comunicação entre os principais blocos do sistema: Frontend, Backend (rotas em `backend/app/api`) e MCP Server. O Backend orquestra as requisições recebidas do Frontend, processa dados, integra serviços internos e se comunica com o MCP Server para processamento de inteligência.

**Descrição dos Blocos:**
- **Frontend:** Interface do usuário, responsável por enviar requisições HTTP para o Backend e consumir respostas.
- **Backend (API):** Camada intermediária que expõe rotas REST via FastAPI, localizadas em `backend/app/api`. Cada rota é responsável por uma parte do fluxo, como autenticação, análise, projetos, sessões e webhooks.
- **MCP Server:** Serviço externo de inteligência que recebe payloads do Backend para processamento de análises e retorna resultados via webhooks.

**Diagrama Mermaid:**

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend (API)
    participant MCP as MCP Server
    FE->>BE: Requisições HTTP (login, análise, projetos, etc)
    BE->>MCP: Payloads de análise (via rotas /analysis)
    MCP-->>BE: Webhooks de resultado (/webhooks/mcp)
    BE-->>FE: Respostas HTTP (dados, status, relatórios)


---

## 2. Login e Autenticação via Azure AD

Fluxo:
1. O frontend envia o token JWT via header Authorization para o endpoint POST `/auth/login` (implementado em [`backend/app/api/auth.py`]).
2. O backend valida o token via `AzureADService`, usando a chave pública do Azure AD (JWKS).
3. O backend extrai o `usuario_executor` dos claims do token (preferred_username, email ou upn).
4. O backend busca os projetos associados ao `usuario_executor` usando `ProjectStateService._fetch_and_sanitize_projects`.
5. O backend retorna para o frontend a lista de projetos de resumo, contendo apenas os campos: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, project_id.

**Nota:** O fluxo de validação do token JWT é orquestrado pela rota `/auth/login` em [`backend/app/api/auth.py`], que utiliza o serviço `AzureADService` para garantir autenticidade e extração segura do usuário.

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

## 3. Criação de Projeto e Conversão nome_projeto → project_id

O frontend deve sempre enviar apenas o campo `nome_projeto` para criação ou início de análise. O backend é responsável por converter internamente o `nome_projeto` para `project_id`:
- Se o projeto já existe, o backend recupera o mesmo `project_id` do estado salvo.
- Se o projeto é novo, o backend gera um novo `project_id` (UUID) e associa ao nome do projeto.
- O `project_id` é retornado na resposta do backend para uso em operações subsequentes.
- O enriquecimento de contexto agora exige usuario_executor e nome_projeto como parâmetros obrigatórios.

**Nota:** Este fluxo é implementado pela rota `/analysis/start` em [`backend/app/api/analysis.py`], que utiliza o serviço `ProjectStateService` para conversão e persistência do identificador do projeto.

Diagrama de Fluxo Atualizado:

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant MCP as MCP Server
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, ...)
    BE->>BE: Converte nome_projeto para project_id (recupera existente ou gera novo)
    BE->>BE: Enriquecimento de contexto (passando usuario_executor, nome_projeto, project_id)
    BE->>MCP: Envia payload (project_id, analysis_type, ...)
    MCP-->>BE: job_id, project_id
    BE-->>FE: message, project_id, nome_projeto

---

## 4. Consulta de Projeto Existente

O Backend permite ao frontend consultar a existência de um projeto pelo nome, retornando o estado associado se encontrado.

**Nota:** Este fluxo é implementado pela rota `/projects/check` em [`backend/app/api/projects.py`], que utiliza o serviço `ProjectStateService` para buscar e validar projetos existentes.

mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (nome_projeto)
    BE->>BE: Busca project_id associado ao nome_projeto
    BE-->>FE: exists: true, state (inclui project_id)

---

## 5. Observações Importantes

- O campo `project_id` nunca deve ser enviado pelo frontend. O backend faz toda a conversão e retorna o `project_id` correto.
- Toda comunicação interna e com MCP utiliza o `project_id` gerado ou recuperado pelo backend.
- O frontend deve usar o `project_id` retornado para todas operações subsequentes (consultas, atualizações, etc).

---

## 6. Enriquecimento de Contexto para Refinamento

Quando o frontend envia um `analysis_type` de refinamento (ex: `refinamento_epicos_azure_devops`), o backend executa um processo de enriquecimento de contexto antes de enviar o payload ao MCP:

1. O backend consulta uma configuração (`ANALYSIS_CONTEXT_CONFIG`) que mapeia o `analysis_type` para uma lista de estados/reports a serem lidos do Blob Storage.
2. Para cada entrada, o backend recupera o estado correspondente usando `ProjectStateService.load_latest_state_from_blob()` e extrai o campo de report relevante (ex: `epicos_report`).
3. O conteúdo do report é serializado em string (usando JSON ou formatação legível).
4. Todos os textos extraídos são concatenados junto com o texto original de `instrucoes_extras` enviado pelo frontend.
5. O texto enriquecido é enviado no campo `comentario_extra` do payload para o MCP.
6. O método de enriquecimento agora exige usuario_executor e nome_projeto como argumentos obrigatórios e repassa corretamente para o serviço de estado.

**Nota:** Este fluxo é orquestrado pela rota `/analysis/start` em [`backend/app/api/analysis.py`] e pelo serviço `ContextEnrichmentService`, garantindo que o contexto enviado ao MCP seja o mais completo possível.

Diagrama Mermaid atualizado:

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant Blob as Blob Storage
    participant MCP as MCP Server
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, instrucoes_extras)
    BE->>BE: Consulta ANALYSIS_CONTEXT_CONFIG para analysis_type
    loop Para cada estado/report
        BE->>Blob: Busca estado e extrai report (usando usuario_executor, nome_projeto, project_id)
        BE->>BE: Serializa report como texto
    end
    BE->>BE: Concatena textos dos reports + instrucoes_extras
    BE->>MCP: Envia payload enriquecido (comentario_extra)
    MCP-->>BE: job_id, project_id
    BE-->>FE: message, project_id, nome_projeto

---
