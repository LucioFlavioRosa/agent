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
      "project_id": "projeto-uuid-123",
      "session_id": "session-uuid-123"
    }
  ],
  "session_id": "session-uuid-123"
}

**Notas importantes:**
- O campo `session_id` retornado no login é sempre o mesmo do estado mais recente do projeto selecionado (extraído do Redis ou Blob Storage). Nunca é gerado novamente para projetos existentes. Apenas para novos projetos (sem estado), um novo `session_id` é criado.
- O identificador único de toda a sessão é sempre o `session_id`, gerado no login e propagado para todas as interações.
- A consistência do `session_id` é garantida em toda a comunicação entre frontend, backend e MCP.

### 1.2 Verificação de Projeto (GET /projects/check)

**Requisição:**

GET /projects/check?projeto=ProjetoNovo HTTP/1.1
Authorization: Bearer <token>

**Resposta (projeto encontrado, sessão ativa no Redis):**

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
    "session_id": "session-uuid-123"
  }
}

**Resposta (projeto encontrado, sessão restaurada do Blob Storage):**

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
    "session_id": "session-uuid-123"
  }
}

**Resposta (projeto não encontrado):**

{
  "exists": false
}

**Notas importantes:**
- O campo `state` sempre reflete o estado mais recente disponível para o projeto, buscando primeiro no Redis (sessão ativa) e, se não encontrado, faz fallback para o Blob Storage.
- O campo `session_id` retornado é sempre o mesmo do estado mais recente (Redis ou Blob). Se a sessão não estiver no Redis, o backend restaura a sessão usando o session_id do Blob antes de retornar o estado.
- O campo `reports` sempre está atualizado conforme o último relatório recebido (via webhook MCP ou atualização manual).
- Se houver diferença entre o estado do Blob Storage e o Redis, o valor do Redis é priorizado.
- O identificador único de toda a sessão é sempre o `session_id`, gerado no login e propagado para todas as interações.

### 1.3 Início de Análise (POST /analysis/start)

**Requisição:**

POST /analysis/start HTTP/1.1
Authorization: Bearer <token>
Content-Type: multipart/form-data

Campos:
- projeto: string
- analysis_type: string
- comentario_usuario: string (opcional)
- project_id: string (opcional)
- file: arquivo DOCX (opcional, obrigatório para novo projeto)
- session_id: string (opcional, reutilizado para projetos existentes)

**Resposta:**

{
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "session-uuid-123",
  "project_id": "projeto-uuid-123"
}

**Notas importantes:**
- O campo `session_id` é sempre reutilizado para projetos existentes (extraído do Redis ou Blob Storage). Apenas para novos projetos, um novo `session_id` é gerado.
- O upload de DOCX e a extração de texto ocorrem de forma paralela dentro do mesmo endpoint. O texto extraído é enviado ao MCP, nunca a URL do arquivo.
- O identificador único de toda a sessão é sempre o `session_id`.

### 1.4 Webhooks MCP → Backend

O MCP deve enviar um POST para o endpoint `/webhooks/mcp` do backend com o seguinte formato JSON:

{
  "session_id": "session-uuid-123",
  "status": "in_progress" | "done" | "error",
  "progress": <opcional, int>,
  "report_type": <string, obrigatório quando status="in_progress" ou "done">,
  "report_data": <dict, obrigatório quando status="in_progress" ou "done">,
  "error_type": <string, obrigatório quando status="error">,
  "error_message": <string, obrigatório quando status="error">,
  "usuario_executor": "user@example.com" (opcional),
  "projeto": "ProjetoNovo" (opcional)
}

**Notas importantes:**
- O backend busca a sessão correspondente usando o `session_id` persistido no Redis. Se não encontrar, busca automaticamente no Blob Storage usando `usuario_executor` e `projeto` (se disponíveis) ou apenas `session_id`.
- Se encontrar o estado no Blob, restaura a sessão no Redis antes de atualizar o relatório.
- O relatório é sempre atualizado corretamente, independentemente do estado do Redis.
- O campo `session_id` é sempre o identificador único e deve ser o mesmo em todas as comunicações.

### 1.5 Salvamento Imediato de Estado no Blob Storage

Após cada atualização de relatório via webhook MCP (ou via endpoint manual), o backend salva imediatamente o estado atualizado no Blob Storage. Isso garante consistência e minimiza perda de dados em caso de falha.

**Fluxo:**
- Webhook MCP recebido → relatório atualizado na sessão → estado salvo imediatamente no Blob Storage (novo arquivo, nunca sobrescreve anterior)
- O campo `session_id` é sempre incluído no nome do arquivo salvo.

### 1.6 Exemplos de Payloads Revisados

Todos os exemplos de payloads abaixo garantem que o campo `session_id` está presente e consistente em todas as requisições e respostas. Não há mais referências a `job_id` ou `analysis_name`.

#### Exemplo de atualização de relatório via webhook MCP

POST /webhooks/mcp

{
  "session_id": "session-uuid-123",
  "status": "done",
  "report_type": "epicos",
  "report_data": { "epicos": [{ "id": 1, "titulo": "Como usuário..."}] },
  "usuario_executor": "user@example.com",
  "projeto": "ProjetoNovo"
}

#### Exemplo de consulta ao estado do projeto

GET /projects/check?projeto=ProjetoNovo
Authorization: Bearer <token>

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
    "session_id": "session-uuid-123"
  }
}

### 1.7 Observações Importantes

- O campo `session_id` é o único identificador usado em toda a comunicação entre frontend, backend e MCP. Nunca é gerado novamente para projetos existentes.
- O backend sempre prioriza o estado do Redis (sessão ativa). Se não encontrar, faz fallback para o Blob Storage e restaura a sessão antes de retornar o estado.
- O campo `reports` reflete imediatamente qualquer atualização feita via webhook do MCP ou via endpoint manual.
- Após cada atualização de relatório, o estado é salvo imediatamente no Blob Storage, criando um novo arquivo (nunca sobrescreve o anterior).
- O upload de DOCX ocorre dentro do endpoint `/analysis/start` via multipart/form-data, e o texto extraído é enviado ao MCP.
- Não há mais referências a `job_id` ou `analysis_name` em nenhum fluxo ou payload.
- O frontend pode confiar que a consulta ao endpoint `/projects/check` sempre retorna o estado mais atualizado possível, priorizando o Redis.
- O MCP nunca gera nenhum identificador próprio: sempre recebe e retorna o `session_id` enviado pelo backend.
- O backend nunca atualiza um registro de sessão já salvo: sempre cria um novo estado com os dados atualizados da sessão.
- A consistência e unicidade do `session_id` são garantidas em toda a comunicação e persistência de estado.
