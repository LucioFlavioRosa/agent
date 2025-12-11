# Índice

- [1. Introdução](#1-introdução)
- [2. Autenticação e Configuração](#2-autenticação-e-configuração)
  - [2.1 Obtenção de Configuração Azure AD (GET /auth/config)](#21-obtenção-de-configuração-azure-ad-get-authconfig)
  - [2.2 Login e Obtenção de Projetos (POST /auth/login)](#22-login-e-obtenção-de-projetos-post-authlogin)
- [3. Gerenciamento de Projetos](#3-gerenciamento-de-projetos)
  - [3.1 Verificar Existência de Projeto (GET /projects/check)](#31-verificar-existência-de-projeto-get-projectscheck)
  - [3.2 Listar Projetos do Usuário (GET /projects/list)](#32-listar-projetos-do-usuário-get-projectslist)
- [4. Início de Análise](#4-início-de-análise)
  - [4.1 Iniciar Análise (POST /analysis/start)](#41-iniciar-análise-post-analysisstart)
- [5. Gerenciamento de Sessão e Relatórios](#5-gerenciamento-de-sessão-e-relatórios)
  - [5.1 Consultar Relatórios do Projeto (GET /session/project/{project_id}/reports)](#51-consultar-relatórios-do-projeto-get-sessionprojectproject_idreports)
  - [5.2 Atualizar Relatório Individual (PUT /session/project/{project_id}/report)](#52-atualizar-relatório-individual-put-sessionprojectproject_idreport)
  - [5.3 Salvar Estado do Projeto (POST /session/project/{project_id}/save-state)](#53-salvar-estado-do-projeto-post-sessionprojectproject_idsave-state)
  - [5.4 Listar Arquivos DOCX do Projeto (GET /session/project/{project_id}/docx-files)](#54-listar-arquivos-docx-do-projeto-get-sessionprojectproject_iddocx-files)
  - [5.5 Consultar Estado Individual de Report (GET /session/project/{project_id}/report/{report_type})](#55-consultar-estado-individual-de-report-get-sessionprojectproject_idreportreport_type)
- [6. Webhooks MCP → Backend](#6-webhooks-mcp--backend)
  - [6.1 Webhook de Progresso/Conclusão/Erro (POST /webhooksmcp)](#61-webhook-de-progresso-conclusão-erro-post-webhooksmcp)
- [7. Tratamento de Erros](#7-tratamento-de-erros)
- [8. Fluxo Completo de Comunicação Frontend ↔ Backend ↔ MCP](#8-fluxo-completo-de-comunicação-frontend-↔-backend-↔-mcp)
- [9. Boas Práticas de Integração](#9-boas-práticas-de-integração)

---

# 1. Introdução

Este documento apresenta exemplos detalhados de payloads, headers, respostas e fluxos para todas as requisições da API do backend Peers CodeAI. O objetivo é orientar o frontend sobre como se comunicar corretamente com a API, como enviar e ler dados, e como interpretar as respostas e erros.

A comunicação segue o fluxo: **Frontend ↔ Backend ↔ MCP**. O backend orquestra autenticação, gerenciamento de projetos, upload de arquivos, envio de análises ao MCP, atualização de relatórios e persistência de estado.

---

# 2. Autenticação e Configuração

## 2.1 Obtenção de Configuração Azure AD (GET /auth/config)

GET /auth/config HTTP/1.1

{
  "client_id": "<client-id>",
  "tenant_id": "<tenant-id>",
  "authority": "https://login.microsoftonline.com/<tenant-id>",
  "redirect_uri": "http://localhost:3000/auth/callback",
  "scope": "User.Read"
}

---
# 2.2 Login e Obtenção de Projetos (POST /auth/login)

Fluxo:
1. O frontend envia o token JWT via header Authorization.
2. O backend valida o token usando AzureADService, extrai o usuario_executor dos claims.
3. O backend busca os projetos associados ao usuario_executor usando ProjectStateService._fetch_and_sanitize_projects.
4. O backend retorna para o frontend a lista de projetos de resumo (campos: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, project_id).
5. **Novo comportamento:** Mesmo que múltiplos estados existam para o mesmo projeto, o backend retorna apenas o estado mais recente de cada projeto único, eliminando duplicatas por project_id ou nome_projeto.

Exemplo de requisição:
POST /auth/login HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

Exemplo de resposta de sucesso:
{
  "user_info": {
    "usuario_executor": "user@example.com",
    "sub": "uuid",
    "name": "Nome do Usuário",
    "email": "user@example.com",
    "roles": ["admin"]
  },
  "projects": [
    {
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "project_id": "projeto-uuid-123"
    }
  ]
}

> **Observação:** Mesmo que existam múltiplos estados para o mesmo projeto, o backend sempre retorna apenas o mais recente para cada projeto único.

Exemplo de resposta de erro (token expirado):
{
  "detail": "Token Azure AD expirado."
}

Exemplo de resposta de erro (token inválido):
{
  "detail": "Token Azure AD inválido: ..."
}
---

# 3. Gerenciamento de Projetos

## 3.1 Verificar Existência de Projeto (GET /projects/check)

GET /projects/check?nome_projeto=ProjetoNovo HTTP/1.1
Authorization: Bearer <token>

{
  "exists": true,
  "state": {
    "resumo": {
      "usuario_executor": "user@example.com",
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "project_id": "projeto-uuid-123"
    },
    "epicos": {
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "epicos_report": [{ "id": 1, "titulo": "Como usuário..." }]
    },
    "features": {
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_features_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "features_report": [{ "id": 101, "nome": "Login" }]
    },
    "times_descricao": {
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_times_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "times_descricao_report": []
    },
    "alocacao_times": {
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_alocacao_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "alocacao_times_report": []
    },
    "premissas_riscos": {
      "nome_projeto": "ProjetoNovo",
      "ultima_analysis_type": "criacao_premissas_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "premissas_riscos_report": []
    }
  }
}

---

## 3.2 Listar Projetos do Usuário (GET /projects/list)

GET /projects/list HTTP/1.1
Authorization: Bearer <token>

[
  {
    "nome_projeto": "ProjetoNovo",
    "ultima_analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "ultima_atualizacao": "2024-06-01T12:30:00Z",
    "project_id": "projeto-uuid-123"
  },
  ...
]

---

# 4. Início de Análise

## 4.1 Iniciar Análise (POST /analysis/start)

O frontend deve enviar apenas o campo `nome_projeto` (e nunca `project_id`). O backend irá internamente converter `nome_projeto` para `project_id` usando o serviço ProjectStateService. Se o projeto já existir, o mesmo `project_id` será utilizado. Se for um novo projeto, o backend irá gerar um novo `project_id` e retornar na resposta.

Exemplo de requisição:
POST /analysis/start HTTP/1.1
Authorization: Bearer <token>
Content-Type: multipart/form-data

nome_projeto=ProjetoNovo
analysis_type=criacao_epicos_azure_devops
instrucoes_extras=Este é um comentário adicional do usuário.
arquivo_docx=<arquivo.docx>

Exemplo de resposta de sucesso:
{
  "message": "Análise solicitada com sucesso ao agente.",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

Observação: O campo `project_id` nunca deve ser enviado pelo frontend. O backend retorna o `project_id` na resposta para uso em operações subsequentes.

---

# 5. Gerenciamento de Sessão e Relatórios

## 5.1 Consultar Relatórios do Projeto (GET /session/project/{project_id}/reports)

GET /session/project/projeto-uuid-123/reports HTTP/1.1
Authorization: Bearer <token>

### Novo comportamento (a partir de 2024-06):

- O endpoint agora verifica se existe um job ativo (status 'pending' ou 'in_progress') para o `project_id`.
- Se houver um job ativo e o campo `request_timestamp` do job for mais recente que o campo `ultima_atualizacao` do estado de resumo no Redis, o endpoint retorna HTTP 202 (Accepted) com mensagem indicando que o processamento está em andamento. Nenhum dado antigo é retornado.
- Se o job ativo tiver status 'done' e o campo `response_timestamp` for mais recente que o campo `ultima_atualizacao` do estado no Redis, o backend busca o estado atualizado do Blob Storage antes de retornar a resposta ao frontend.
- Isso garante que o frontend só recebe o estado correspondente à última requisição enviada ao MCP, evitando inconsistências.

#### Exemplo de resposta quando há processamento em andamento (HTTP 202):

Status: 202 Accepted

{
  "status": "processing",
  "message": "O processamento da última requisição está em andamento. Aguarde a conclusão do MCP para obter o resultado atualizado.",
  "project_id": "projeto-uuid-123"
}

#### Exemplo de resposta quando o processamento foi concluído e o estado está atualizado:

Status: 200 OK

{
  "resumo": {
    "usuario_executor": "user@example.com",
    "nome_projeto": "ProjetoNovo",
    "ultima_analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "ultima_atualizacao": "2024-06-01T12:31:00Z",
    "project_id": "projeto-uuid-123"
  },
  "epicos": {
    "nome_projeto": "ProjetoNovo",
    "ultima_analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "ultima_atualizacao": "2024-06-01T12:31:00Z",
    "epicos_report": [{ "id": 1, "titulo": "Como usuário..." }]
  },
  "features": {
    "nome_projeto": "ProjetoNovo",
    "ultima_analysis_type": "criacao_features_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "ultima_atualizacao": "2024-06-01T12:31:00Z",
    "features_report": [{ "id": 101, "nome": "Login" }]
  },
  ...
}

---

## 5.2 Atualizar Relatório Individual (PUT /session/project/{project_id}/report)

PUT /session/project/projeto-uuid-123/report HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "report_data": {
    "features_report": [
      { "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" }
    ]
  }
}

{
  "status": "ok",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

---

## 5.3 Salvar Estado do Projeto (POST /session/project/{project_id}/save-state)

POST /session/project/projeto-uuid-123/save-state HTTP/1.1
Authorization: Bearer <token>

{
  "blob_url": "https://.../estado_resumo_20240601T123000Z.json",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

---

## 5.4 Listar Arquivos DOCX do Projeto (GET /session/project/{project_id}/docx-files)

GET /session/project/projeto-uuid-123/docx-files HTTP/1.1
Authorization: Bearer <token>

{
  "docx_files": ["https://.../arquivo1.docx", "https://.../arquivo2.docx"],
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

---

## 5.5 Consultar Estado Individual de Report (GET /session/project/{project_id}/report/{report_type})

GET /session/project/projeto-uuid-123/report/epicos_report HTTP/1.1
Authorization: Bearer <token>

{
  "nome_projeto": "ProjetoNovo",
  "ultima_analysis_type": "criacao_epicos_azure_devops",
  "created_at": "2024-06-01T12:00:00Z",
  "ultima_atualizacao": "2024-06-01T12:30:00Z",
  "epicos_report": [
    { "id": 1, "titulo": "Como usuário..." }
  ]
}

GET /session/project/projeto-uuid-123/report/features_report HTTP/1.1
Authorization: Bearer <token>

{
  "nome_projeto": "ProjetoNovo",
  "ultima_analysis_type": "criacao_features_azure_devops",
  "created_at": "2024-06-01T12:00:00Z",
  "ultima_atualizacao": "2024-06-01T12:30:00Z",
  "features_report": [
    { "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" }
  ]
}

GET /session/project/projeto-uuid-123/report/times_descricao_report HTTP/1.1
Authorization: Bearer <token>

{
  "nome_projeto": "ProjetoNovo",
  "ultima_analysis_type": "criacao_times_azure_devops",
  "created_at": "2024-06-01T12:00:00Z",
  "ultima_atualizacao": "2024-06-01T12:30:00Z",
  "times_descricao_report": []
}

GET /session/project/projeto-uuid-123/report/alocacao_times_report HTTP/1.1
Authorization: Bearer <token>

{
  "nome_projeto": "ProjetoNovo",
  "ultima_analysis_type": "criacao_alocacao_azure_devops",
  "created_at": "2024-06-01T12:00:00Z",
  "ultima_atualizacao": "2024-06-01T12:30:00Z",
  "alocacao_times_report": []
}

GET /session/project/projeto-uuid-123/report/premissas_riscos_report HTTP/1.1
Authorization: Bearer <token>

{
  "nome_projeto": "ProjetoNovo",
  "ultima_analysis_type": "criacao_premissas_azure_devops",
  "created_at": "2024-06-01T12:00:00Z",
  "ultima_atualizacao": "2024-06-01T12:30:00Z",
  "premissas_riscos_report": []
}

---

# 6. Webhooks MCP → Backend

## 6.1 Webhook de Progresso/Conclusão/Erro (POST /webhooks/mcp)

POST /webhooks/mcp HTTP/1.1
Content-Type: application/json

{
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_data": {
    "features_report": [
      { "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" },
      { "id": 102, "nome": "Middleware de Validação JWT", "descricao": "Validar token no backend Python" }
    ]
  },
  "analysis_type": "criacao_features_azure_devops"
}

{
  "status": "ok",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

---

# 7. Tratamento de Erros

{
  "detail": "Token Azure AD expirado."
}

---

# 8. Fluxo Completo de Comunicação Frontend ↔ Backend ↔ MCP

## 8.1 Novo Projeto

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant MCP as MCP Server
    FE->>BE: POST /auth/login (token)
    BE-->>FE: Lista de projetos (resumo: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, project_id)
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, instrucoes_extras, arquivo_docx)
    BE->>BE: Converte nome_projeto para project_id (gera novo se não existir)
    BE->>MCP: Envia payload (project_id, analysis_type, instrucoes_extras, texto extraído)
    MCP-->>BE: job_id, project_id
    BE-->>FE: message, project_id, nome_projeto

## 8.2 Projeto Existente

mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (nome_projeto)
    BE-->>FE: exists: true, state (resumo + todos os estados disponíveis)
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, ...)
    BE->>BE: Converte nome_projeto para project_id (recupera existente)
    BE->>MCP: Envia payload
    MCP-->>BE: job_id, project_id
    BE-->>FE: message, project_id, nome_projeto

## 8.3 Atualização de Relatório via Webhook

mermaid
sequenceDiagram
    MCP->>BE: Webhook (job_id, project_id, status, report_data, analysis_type)
    BE->>BE: Usa analysis_type para determinar report_type
    BE->>RS: Atualiza estado individual do report (ex: features_report)
    BE->>BS: Salva estado individual do report no Blob Storage (pasta específica)
    BE-->>FE: status ok

## 8.4 Consulta de Estado Individual de Report

mermaid
sequenceDiagram
    FE->>BE: GET /session/project/{project_id}/report/{report_type}
    BE->>RS: Busca estado individual do report
    BE-->>FE: Estado individual do report (campos: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, <report_field>)

## 8.5 Consulta de Estado Completo do Projeto

mermaid
sequenceDiagram
    FE->>BE: GET /session/project/{project_id}/reports
    BE->>BS: Busca todos os estados salvos no Blob Storage
    BE-->>FE: Retorna todos os estados (resumo + reports disponíveis)

---

# 9. Boas Práticas de Integração

- Sempre utilize o campo `project_id` para identificar projetos em todas as requisições subsequentes.
- Para obter o estado completo do projeto, utilize o endpoint `GET /session/project/{project_id}/reports` ou `GET /projects/check`.
- O backend mantém um estado de resumo do projeto e estados individuais para cada report, cada um salvo em sua pasta específica no Blob Storage.
- O campo `ultima_analysis_type` indica qual foi a última análise executada no projeto ou report.
- O backend atualiza apenas o estado do report correspondente ao `analysis_type` recebido no webhook.
- O frontend deve fazer polling periódico para consultar estados de reports enquanto o MCP processa a análise.
