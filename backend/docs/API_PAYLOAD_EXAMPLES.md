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

### 1.2 Verificação de Projeto (GET /projects/check)

**Requisição:**

GET /projects/check?projeto=ProjetoNovo HTTP/1.1
Authorization: Bearer <token>

**Resposta (projeto encontrado):**

{
  "exists": true,
  "state": {
    "usuario_executor": "user@example.com",
    "projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "reports": {
      "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..."}]},
      "features_report": { "features": [{ "id": 1, "nome": "Login"}]}
    },
    "docx_files": ["https://.../arquivo1.docx"],
    "comentario_usuario": "Comentário salvo",
    "extracted_text": "Texto extraído do arquivo DOCX da reunião",
    "project_id": "projeto-uuid-123",
    "last_mcp_job_id": "123456"
  }
}

**Nota importante:**
- O campo `state` sempre reflete o estado mais recente disponível para o projeto, buscando **primeiro no Redis** (sessão ativa) e, se não encontrado, faz fallback para o Blob Storage.
- O campo `reports` sempre está atualizado conforme o último relatório recebido (via webhook MCP ou atualização manual).
- Se houver diferença entre o estado do Blob Storage e o Redis, o valor do Redis é priorizado.

**Resposta (projeto não encontrado):**

{
  "exists": false
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

**Campos obrigatórios:**
- `job_id`: string. Identificador do job retornado pelo backend ao MCP.
- `status`: string. Um dos valores: `in_progress`, `done`, `error`.
- `progress`: inteiro opcional (0-100), só para status `in_progress`.
- `report_type`: string. Obrigatório para status `in_progress` ou `done`. Exemplo: `epicos`, `features`, `tech_debt`.
- `report_data`: objeto/dict. Obrigatório para status `in_progress` ou `done`. Estrutura depende do tipo de relatório.
- `error_type`: string. Obrigatório para status `error`.
- `error_message`: string. Obrigatório para status `error`.

> **Nota:** O backend busca a sessão correspondente usando o job_id persistido no Redis. Se não encontrar, retorna 404 e loga o erro detalhadamente.

---

## 3. Exemplos de Respostas Backend → Frontend (Principais Endpoints)

### 3.1 /projects/check
**Sucesso:**

{
  "exists": true,
  "state": {
    "usuario_executor": "user@example.com",
    "projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "reports": { "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..."}]}},
    "docx_files": ["https://.../arquivo1.docx"],
    "comentario_usuario": "Comentário salvo",
    "extracted_text": "Texto extraído do arquivo DOCX da reunião",
    "project_id": "projeto-uuid-123",
    "last_mcp_job_id": "123456"
  }
}

**Nota:** O campo `state` sempre reflete o estado mais recente disponível, buscando primeiro no Redis (sessão ativa) e, se não encontrado, faz fallback para o Blob Storage. O campo `reports` está sempre atualizado com o último relatório recebido.

**Projeto não encontrado:**

{
  "exists": false
}

---

## 4. Observações Importantes
- O endpoint `/projects/check` sempre retorna o estado mais recente disponível para o projeto, priorizando o Redis.
- O campo `reports` reflete imediatamente qualquer atualização feita via webhook do MCP ou via endpoint manual.
- Se a sessão estiver ativa no Redis, o estado retornado é o do Redis (incluindo relatórios mais recentes). Se não houver sessão ativa, o backend retorna o último estado salvo no Blob Storage.
- O campo `state` nunca mistura dados de fontes diferentes: sempre é 100% do Redis ou 100% do Blob Storage.
- O frontend pode confiar que a consulta ao endpoint `/projects/check` sempre retorna o estado mais atualizado possível.

---

## 5. Fluxo Completo de Comunicação (Exemplo End-to-End)

### 1. Login

POST /auth/login
Authorization: Bearer <token>

Resposta:

{
  "user_info": { "usuario_executor": "user@example.com", "sub": "uuid", "name": "Nome do Usuário", "email": "user@example.com", "roles": ["admin"]},
  "projects": [{ "projeto": "ProjetoNovo", "analysis_type": "criacao_epicos_azure_devops", "created_at": "2024-06-01T12:00:00Z", "last_saved_to_blob": "2024-06-01T12:30:00Z", "project_id": "projeto-uuid-123"}]
}

### 2. Verificação de Projeto

GET /projects/check?projeto=ProjetoNovo
Authorization: Bearer <token>

Resposta:

{
  "exists": true,
  "state": {
    "usuario_executor": "user@example.com",
    "projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "reports": { "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..."}]}},
    "docx_files": ["https://.../arquivo1.docx"],
    "comentario_usuario": "Comentário salvo",
    "extracted_text": "Texto extraído do arquivo DOCX da reunião",
    "project_id": "projeto-uuid-123",
    "last_mcp_job_id": "123456"
  }
}

---

## Notas
- Todos os exemplos de requisição (exceto `/auth/config`) exigem o header `Authorization: Bearer <token>`.
- O campo `project_id` está presente em todas as respostas de endpoints que envolvem projetos ou sessões.
- O campo `arquivo_docx` enviado para o MCP sempre contém o texto extraído do DOCX, nunca a URL.
- Todos os relatórios estão sob o campo unificado `reports`. Campos legados como `epicos_report` ainda podem aparecer para retrocompatibilidade, mas o padrão é usar o objeto `reports`.
- O upload de DOCX ocorre dentro do endpoint `/analysis/start` via multipart/form-data.
- Para erros, o backend sempre retorna o campo `detail` no corpo JSON.
- Após o início da análise, a relação job_id -> session_id é persistida no Redis para garantir que o webhook do MCP encontre a sessão correta.
- Após cada atualização de relatório via webhook do MCP, o estado é salvo imediatamente no Blob Storage e o Redis é atualizado, garantindo consistência e minimizando perda de dados em caso de falha.
- O endpoint `/projects/check` sempre retorna o estado mais recente disponível, priorizando o Redis.
