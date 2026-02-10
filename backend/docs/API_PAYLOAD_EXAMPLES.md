# Índice

- [1. Introdução](#1-introdução)
- [2. Comunicação e Payloads](#2-comunicação-e-payloads)
  - [2.1 Início de Análise (POST /analysis/start)](#21-início-de-análise-post-analysisstart)
  - [2.2 Consulta de Relatórios (GET /session/project/{project_id}/{job_id}/reports)](#22-consulta-de-relatórios-get-sessionprojectproject_idjob_idreports)
- [3. Webhooks MCP → Backend](#3-webhooks-mcp--backend)
- [4. Fluxo Completo de Comunicação Frontend ↔ Backend ↔ MCP](#4-fluxo-completo-de-comunicação-frontend-↔-backend-↔-mcp)
- [5. Boas Práticas de Integração](#5-boas-práticas-de-integração)

---

# 1. Introdução

Este documento apresenta exemplos detalhados de payloads, headers, respostas e fluxos para todas as requisições da API do backend Peers CodeAI. O objetivo é orientar o frontend sobre como se comunicar corretamente com a API, como enviar e ler dados, e como interpretar as respostas e erros.

A comunicação segue o fluxo: **Frontend ↔ Backend ↔ MCP**. O backend apenas repassa as requisições para o MCP e retorna as respostas ao frontend, sem processamento, validação de estrutura de relatórios ou extração de arquivos/docx.

---

# 2. Comunicação e Payloads

## 2.1 Início de Análise (POST /analysis/start)

O frontend deve enviar os campos `email` e `empresa` do usuário (não há autenticação JWT). O backend irá repassar o payload para o MCP, sem processar arquivos ou validar relatórios.

Exemplo de requisição:
POST /analysis/start HTTP/1.1
Content-Type: application/json

{
  "email": "user@example.com",
  "empresa": "Peers",
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

## 2.2 Consulta de Relatórios (GET /session/project/{project_id}/{job_id}/reports)

GET /session/project/projeto-uuid-123/job-uuid-456/reports HTTP/1.1

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

# 3. Webhooks MCP → Backend

## 3.1 Webhook de Progresso/Conclusão/Erro (POST /webhooks/mcp)

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

# 4. Fluxo Completo de Comunicação Frontend ↔ Backend ↔ MCP

## 4.1 Novo Projeto

mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend
    participant MCP as MCP Server
    FE->>BE: POST /analysis/start (email, empresa, nome_projeto, analysis_type, comentario_extra)
    BE->>MCP: Repassa payload sem processamento
    MCP-->>BE: job_id, project_id, report_data
    BE-->>FE: message, project_id, nome_projeto

## 4.2 Consulta de Relatório

mermaid
sequenceDiagram
    FE->>BE: GET /session/project/{project_id}/{job_id}/reports
    BE->>MCP: Consulta report_data
    MCP-->>BE: Retorna report_data
    BE-->>FE: Retorna report_data

---

# 5. Boas Práticas de Integração

- Sempre utilize o campo `project_id` para identificar projetos em todas as requisições subsequentes.
- Para obter o relatório do projeto, utilize o endpoint `GET /session/project/{project_id}/{job_id}/reports`.
- O backend repassa o conteúdo de report_data do MCP diretamente ao frontend, sem validação ou processamento.
- O frontend deve fazer polling periódico para consultar estados de reports enquanto o MCP processa a análise.
- O backend não processa arquivos docx nem valida relatórios; toda extração e persistência é responsabilidade do MCP.
- O frontend é responsável por autenticação e envio dos dados do usuário (email, empresa).
