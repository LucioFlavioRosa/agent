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

## 2. Criação de Projeto, Geração de job_id e Conversão nome_projeto → project_id

O frontend deve sempre enviar apenas o campo `nome_projeto` para criação ou início de análise. O backend é responsável por converter internamente o `nome_projeto` para `project_id`:
- Se o projeto já existe, o backend recupera o mesmo `project_id` do estado salvo.
- Se o projeto é novo, o backend gera um novo `project_id` (UUID) e associa ao nome do projeto.
- Antes de enviar o payload ao MCP, o backend gera um `job_id` (UUID) exclusivo e associa ao projeto/analise.
- O `job_id` é incluído no payload enviado ao MCP e também retornado ao frontend.
- O `project_id` e o `job_id` são retornados na resposta do backend para uso em operações subsequentes.
- O enriquecimento de contexto agora exige usuario_executor e nome_projeto como parâmetros obrigatórios.

Diagrama de Fluxo Atualizado:

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant MCP as MCP Server
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, ...)
    BE->>BE: Converte nome_projeto para project_id (recupera existente ou gera novo)
    BE->>BE: Gera job_id e associa ao projeto/analise
    BE->>BE: Enriquecimento de contexto (passando usuario_executor, nome_projeto, project_id)
    BE->>MCP: Envia payload (project_id, job_id, analysis_type, ...)
    MCP-->>BE: Confirmação de recebimento
    BE-->>FE: message, project_id, job_id, nome_projeto

---

## 3. Consulta de Projeto Existente

mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (nome_projeto)
    BE->>BE: Busca project_id associado ao nome_projeto
    BE-->>FE: exists: true, state (inclui project_id)

---

## 4. Consulta de Reports com job_id

- O frontend deve consultar o endpoint de reports usando o parâmetro `job_id` para acompanhar o status do processamento.
- O backend verifica o status do job no Redis:
    - Se o job estiver 'pending' ou 'in_progress', retorna status 202 (Accepted) e mensagem de processamento.
    - Se o job estiver 'done', retorna os reports normalmente (status 200).
    - Se o job não existir ou estiver em erro, retorna status 404 ou 400.

mermaid
sequenceDiagram
    FE->>BE: GET /session/project/{project_id}/reports?job_id=job-uuid-456
    BE->>RS: Busca status do job no Redis
    alt Job 'pending' ou 'in_progress'
        BE-->>FE: status 202 (processing)
    else Job 'done'
        BE->>BS: Busca todos os estados salvos no Blob Storage
        BE-->>FE: Retorna todos os estados (resumo + reports disponíveis)
    else Job não existe ou erro
        BE-->>FE: status 404 ou 400
    end

---

## 5. Atualização de Relatório via Webhook e Status do Job

- O MCP envia webhooks para o backend informando status do job e dados do relatório.
- O backend atualiza o status do job no Redis conforme o status recebido ('in_progress', 'done', 'error').
- O backend atualiza o estado do report correspondente ao analysis_type recebido.

mermaid
sequenceDiagram
    MCP->>BE: Webhook (job_id, project_id, status, report_data, analysis_type)
    BE->>BE: Usa analysis_type para determinar report_type
    BE->>RS: Atualiza estado individual do report (ex: features_report)
    BE->>BS: Salva estado individual do report no Blob Storage (pasta específica)
    BE->>BE: Atualiza status do job no Redis conforme status recebido
    BE-->>FE: status ok

---

## 6. Observações Importantes

- O campo `project_id` nunca deve ser enviado pelo frontend. O backend faz toda a conversão e retorna o `project_id` correto.
- Toda comunicação interna e com MCP utiliza o `project_id` e o `job_id` gerados ou recuperados pelo backend.
- O frontend deve usar o `project_id` e o `job_id` retornados para todas operações subsequentes (consultas, atualizações, etc).
- O endpoint de consulta de reports agora exige o parâmetro `job_id` para acompanhamento do processamento.
- O backend retorna status HTTP 202 (Accepted) para jobs em andamento, 200 para jobs concluídos, e 404/400 para jobs inexistentes ou com erro.
- O frontend deve fazer polling periódico usando o `job_id` para verificar o status do processamento.

---

## 7. Enriquecimento de Contexto para Refinamento

Quando o frontend envia um `analysis_type` de refinamento (ex: `refinamento_epicos_azure_devops`), o backend executa um processo de enriquecimento de contexto antes de enviar o payload ao MCP:

1. O backend consulta uma configuração (`ANALYSIS_CONTEXT_CONFIG`) que mapeia o `analysis_type` para uma lista de estados/reports a serem lidos do Blob Storage.
2. Para cada entrada, o backend recupera o estado correspondente usando `ProjectStateService.load_latest_state_from_blob()` e extrai o campo de report relevante (ex: `epicos_report`).
3. O conteúdo do report é serializado em string (usando JSON ou formatação legível).
4. Todos os textos extraídos são concatenados junto com o texto original de `instrucoes_extras` enviado pelo frontend.
5. O texto enriquecido é enviado no campo `comentario_extra` do payload para o MCP.
6. O método de enriquecimento agora exige usuario_executor e nome_projeto como argumentos obrigatórios e repassa corretamente para o serviço de estado.

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
    BE-->>FE: message, project_id, job_id, nome_projeto

---
