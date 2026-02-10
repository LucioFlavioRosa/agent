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
  - [5.1 Consultar Relatórios do Projeto (GET /session/project/{project_id}/{job_id}/reports)](#51-consultar-relatórios-do-projeto-get-sessionprojectproject_idreports)
- [6. Webhooks MCP → Backend](#6-webhooks-mcp--backend)
  - [6.1 Webhook de Progresso/Conclusão/Erro (POST /webhooksmcp)](#61-webhook-de-progresso-conclusão-erro-post-webhooksmcp)
- [7. Tratamento de Erros](#7-tratamento-de-erros)
- [8. Fluxo Completo de Comunicação Frontend ↔ Backend ↔ MCP](#8-fluxo-completo-de-comunicação-frontend-↔-backend-↔-mcp)
- [9. Boas Práticas de Integração](#9-boas-práticas-de-integração)

---

# 1. Introdução

Este documento apresenta exemplos detalhados de payloads, headers, respostas e fluxos para todas as requisições da API do backend Peers CodeAI. O objetivo é orientar o frontend sobre como se comunicar corretamente com a API, como enviar e ler dados, e como interpretar as respostas e erros.

A comunicação segue o fluxo: **Frontend ↔ Backend ↔ MCP**. O backend orquestra autenticação, gerenciamento de projetos, repassa payloads para o MCP e retorna respostas ao frontend sem processamento ou validação de estrutura de relatórios.

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
3. O backend busca os projetos associados ao usuario_executor.
4. O backend retorna para o frontend a lista de projetos de resumo (campos: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, project_id).

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
Content-Type: application/json

{
  "nome_projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_extra": "Este é um comentário adicional do usuário."
}

Exemplo de resposta de sucesso:
{
  "message": "Análise solicitada com sucesso ao agente.",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

Observação: O campo `project_id` nunca deve ser enviado pelo frontend. O backend retorna o `project_id` na resposta para uso em operações subsequentes.

---

# 5. Gerenciamento de Sessão e Relatórios

## 5.1 Consultar Relatórios do Projeto (GET /session/project/{project_id}/{job_id}/reports)

GET /session/project/projeto-uuid-123/reports HTTP/1.1
Authorization: Bearer <token>

### Novo comportamento (a partir de 2024-06):

- O endpoint verifica se existe um job ativo (status 'pending' ou 'in_progress') para o `project_id`.
- Se houver um job ativo, retorna HTTP 202 (Accepted) com mensagem indicando que o processamento está em andamento.
- Quando o job for concluído, retorna o conteúdo de `report_data` diretamente do Redis, sem validação ou processamento.

#### Exemplo de resposta quando há processamento em andamento (HTTP 202):

Status: 202 Accepted

{
  "status": "processing",
  "message": "O processamento da última requisição está em andamento. Aguarde a conclusão do MCP para obter o resultado atualizado.",
  "project_id": "projeto-uuid-123"
}

#### Exemplo de resposta quando o processamento foi concluído:

Status: 200 OK

{
  "report_data": {
    "features_report": [
      { "id": 101, "nome": "Login" },
      { "id": 102, "nome": "Cadastro" }
    ]
  },
  "job_id": "job-uuid-456",
  "project_id": "projeto-uuid-123"
}

---

# 6. Webhooks MCP → Backend

## 6.1 Webhook de Progresso/Conclusão/Erro (POST /webhooks/mcp)

POST /webhooks/mcp HTTP/1.1
Content-Type: application/json

{
  "job_id": "job-uuid-456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_data": {
    "features_report": [
      { "id": 101, "nome": "Login" },
      { "id": 102, "nome": "Cadastro" }
    ]
  }
}

{
  "status": "ok",
  "project_id": "projeto-uuid-123"
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
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, comentario_extra)
    BE->>BE: Converte nome_projeto para project_id (gera novo se não existir)
    BE->>MCP: Envia payload (project_id, analysis_type, comentario_extra)
    MCP-->>BE: job_id, project_id, report_data
    BE-->>FE: message, project_id, nome_projeto

## 8.2 Projeto Existente

mermaid
sequenceDiagram
    FE->>BE: GET /projects/check (nome_projeto)
    BE-->>FE: exists: true, state (resumo)
    FE->>BE: POST /analysis/start (nome_projeto, analysis_type, comentario_extra)
    BE->>BE: Converte nome_projeto para project_id (recupera existente)
    BE->>MCP: Envia payload
    MCP-->>BE: job_id, project_id, report_data
    BE-->>FE: message, project_id, nome_projeto

## 8.3 Consulta de Relatório

mermaid
sequenceDiagram
    FE->>BE: GET /session/project/{project_id}/{job_id}/reports
    BE->>Redis: Busca report_data
    BE-->>FE: Retorna report_data

---

# 9. Boas Práticas de Integração

- Sempre utilize o campo `project_id` para identificar projetos em todas as requisições subsequentes.
- Para obter o relatório do projeto, utilize o endpoint `GET /session/project/{project_id}/{job_id}/reports`.
- O backend repassa o conteúdo de report_data do MCP diretamente ao frontend, sem validação ou processamento.
- O frontend deve fazer polling periódico para consultar estados de reports enquanto o MCP processa a análise.
