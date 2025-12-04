# Exemplos de Payloads: Comunicação Frontend ↔ Backend ↔ MCP

Este documento apresenta exemplos práticos de payloads enviados pelo frontend para o backend Peers CodeAI, exemplos de respostas do backend para o frontend, exemplos de respostas do MCP para o backend, e o fluxo completo de comunicação. Inclui exemplos de chamadas HTTP, headers, corpo da requisição e respostas esperadas.

---

## 1. Exemplos de Payloads por Cenário de Uso

### 1.1 Login (POST /auth/login)

**Requisição:**

POST /auth/login HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

**Resposta:**

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
      "projeto": "ProjetoNovo",
      "analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "last_saved_to_blob": "2024-06-01T12:30:00Z",
      "project_id": "projeto-uuid-123"
    }
  ]
}

### 1.2 Exemplo de múltiplos webhooks MCP para a mesma sessão (sobrescrita total)

**Cenário:** MCP envia dois webhooks para o mesmo job_id/session_id, cada um com report_data diferente. O backend sobrescreve completamente o relatório anterior.

**Webhook 1:**

POST /webhooks/mcp

{
  "job_id": "123456",
  "status": "done",
  "report_type": "epicos",
  "report_data": {
    "epicos": [
      { "id": 1, "titulo": "Como usuário...", "descricao": "Primeira versão" }
    ]
  }
}

**Webhook 2 (novo relatório, estrutura diferente):**

POST /webhooks/mcp

{
  "job_id": "123456",
  "status": "done",
  "report_type": "epicos",
  "report_data": {
    "epicos": [
      { "id": 2, "titulo": "Como admin...", "descricao": "Segunda versão" }
    ]
  }
}

**Comportamento esperado:**
- Após o Webhook 1, o campo `epicos_report` na sessão e no Blob Storage contém apenas o relatório do Webhook 1.
- Após o Webhook 2, o campo `epicos_report` é sobrescrito e contém **apenas** o relatório do Webhook 2. Nenhum dado antigo é mantido ou mesclado.

**Exemplo de consulta após ambos webhooks:**

GET /session/abcdef-uuid/reports

{
  "epicos_report": {
    "epicos": [
      { "id": 2, "titulo": "Como admin...", "descricao": "Segunda versão" }
    ]
  }
}

### 1.3 Atualização de Relatório (PUT /session/{session_id}/report)

PUT /session/abcdef-uuid/report HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "report_type": "epicos",
  "report_data": { "epicos": [{ "id": 1, "titulo": "Como usuário..."}]}
}

**Resposta:**

{
  "status": "ok"
}

---

## 2. Exemplos de Webhooks MCP → Backend

### 2.1 Formato Geral do Webhook

O MCP deve enviar um POST para o endpoint `/webhooks/mcp` do backend com o seguinte formato JSON:

{
  "job_id": "<string>",
  "status": "in_progress" | "done" | "error",
  "progress": <opcional, int>,
  "report_type": <string, obrigatório quando status="in_progress" ou "done">,
  "report_data": <dict, obrigatório quando status="in_progress" ou "done">,
  "error_type": <string, obrigatório quando status="error">,
  "error_message": <string, obrigatório quando status="error">
}

**Importante:**
- Toda vez que o MCP responde para o backend, o relatório anterior é removido e o novo sobrescreve completamente o campo correspondente. Nunca ocorre mescla ou manutenção de dados antigos.
- O backend valida explicitamente que o relatório armazenado é idêntico ao recebido do MCP. Se houver divergência, a operação é abortada.

---
