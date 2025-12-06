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
      "nome_projeto": "ProjetoNovo",
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
    "nome_projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]},
    "features_report": { "features": [{ "id": 1, "nome": "Login" }]},
    "times_descricao_report": null,
    "alocacao_times_report": null,
    "premissas_riscos_report": null,
    "docx_files": ["https://.../arquivo1.docx"],
    "comentario_usuario": "Comentário salvo",
    "extracted_text": "Texto extraído do arquivo DOCX da reunião",
    "project_id": "projeto-uuid-123"
  }
}

**Resposta (projeto não encontrado):**

{ 
  "exists": false
}

### 1.3 Upload de DOCX (POST /upload/docx)

**Requisição:**

POST /upload/docx HTTP/1.1
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<arquivo.docx>
projeto=ProjetoNovo
analysis_type=criacao_epicos_azure_devops
comentario_usuario=Comentário opcional

**Resposta:**

{ 
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "session_id": "ghijkl-uuid",
  "job_id": "ghijkl-uuid",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.4 Início de Análise (POST /analysis/start)

**Requisição (projeto novo):**

POST /analysis/start HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{ 
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário."
}

**Requisição (projeto existente, sem novo upload):**

POST /analysis/start HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{ 
  "projeto": "ProjetoExistente",
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_usuario": "Comentário sem arquivo."
}

**Fluxo interno:**
- O backend recebe o campo "projeto" (nome legível do projeto) do frontend.
- O backend busca o project_id correspondente ao nome do projeto (se existir); caso contrário, gera um novo project_id.
- Todas as operações internas e comunicação com o MCP passam a usar project_id como identificador principal.
- O backend pode enviar nome_projeto na resposta para exibição no frontend.

**Payload enviado do backend para o MCP:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário.",
  "usuario_executor": "user@example.com",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

> **Nota:** O campo project_id é sempre utilizado como identificador principal na comunicação com o MCP. O campo nome_projeto é enviado apenas para log/debug.

**Resposta:**

{ 
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.5 Atualização de Relatório (PUT /session/{session_id}/report)

**Requisição:**

PUT /session/abcdef-uuid/report HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{ 
  "report_type": "epicos",
  "report_data": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]}
}

**Resposta:**

{ 
  "status": "ok",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.6 Consulta de Relatórios (GET /session/{session_id}/reports)

**Requisição:**

GET /session/abcdef-uuid/reports HTTP/1.1
Authorization: Bearer <token>

**Resposta:**

{ 
  "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]},
  "features_report": { "features": [{ "id": 1, "nome": "Login" }]},
  "times_descricao_report": null,
  "alocacao_times_report": null,
  "premissas_riscos_report": null,
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

---

## 2. Exemplos de Webhooks MCP → Backend

### 2.1 Formato Geral do Webhook

O MCP deve enviar um POST para o endpoint `/webhooks/mcp` do backend com o seguinte formato JSON:

{ 
  "job_id": "<string>",
  "project_id": "<string>",
  "status": "in_progress" | "done" | "error",
  "progress": <opcional, int>,
  "report_type": <string, obrigatório quando status="in_progress" ou "done">,
  "report_data": <dict, obrigatório quando status="in_progress" ou "done">,
  "error_type": <string, obrigatório quando status="error">,
  "error_message": <string, obrigatório quando status="error">
}

**Campos obrigatórios:**
- `job_id`: string. Identificador do job retornado pelo backend ao MCP.
- `project_id`: string. Identificador único do projeto, usado para buscar a sessão correspondente.
- `status`: string. Um dos valores: `in_progress`, `done`, `error`.
- `progress`: inteiro opcional (0-100), só para status `in_progress`.
- `report_type`: string. Obrigatório para status `in_progress` ou `done`. Exemplo: `epicos`, `features`, `tech_debt`.
- `report_data`: objeto/dict. Obrigatório para status `in_progress` ou `done`. Estrutura depende do tipo de relatório.
- `error_type`: string. Obrigatório para status `error`.
- `error_message`: string. Obrigatório para status `error`.

> **Nota:** O backend busca a sessão correspondente usando o project_id persistido no Redis. Se não encontrar, retorna 404 e loga o erro detalhadamente.

### 2.2 Exemplos de Webhook para Cada Tipo de Relatório

#### 2.2.1 Webhook de Progresso (`status: in_progress`)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "in_progress",
  "progress": 40,
  "report_type": "epicos",
  "report_data": { 
    "epicos": [
      { "id": 1, "titulo": "Como usuário..." }
    ]
  }
}

#### 2.2.2 Webhook de Conclusão (`status: done`)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_type": "epicos",
  "report_data": { 
    "epicos": [
      { "id": 1, "titulo": "Como usuário...", "descricao": "..." },
      { "id": 2, "titulo": "Como admin...", "descricao": "..." }
    ]
  }
}

#### 2.2.3 Webhook de Erro (`status: error`)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "error",
  "error_type": "timeout",
  "error_message": "Tempo limite excedido ao processar análise."
}

#### 2.2.4 Webhook para Features (`status: done`)

{ 
  "job_id": "7891011",
  "project_id": "projeto-uuid-456",
  "status": "done",
  "report_type": "features",
  "report_data": { 
    "features": [
      { "id": 1, "nome": "Login", "descricao": "Permitir login com Azure AD" }
    ]
  }
}

#### 2.2.5 Webhook para Tech Debt (`status: done`)

{ 
  "job_id": "555777",
  "project_id": "projeto-uuid-789",
  "status": "done",
  "report_type": "tech_debt",
  "report_data": { 
    "tech_debt": [
      { "id": 1, "descricao": "Código duplicado" }
    ]
  }
}

### 2.3 Estrutura de report_data Esperada por Tipo

- Para `report_type: "epicos"`:
  - `report_data` deve conter a chave `epicos` com uma lista de épicos:
    
    {
      "epicos": [
        { "id": 1, "titulo": "Como usuário...", "descricao": "..." }
      ]
    }
    
- Para `report_type: "features"`:
  - `report_data` deve conter a chave `features` com uma lista de features:
    
    {
      "features": [
        { "id": 1, "nome": "Login", "descricao": "Permitir login com Azure AD" }
      ]
    }
    
- Para `report_type: "tech_debt"`:
  - `report_data` deve conter a chave `tech_debt` com uma lista de itens de débito técnico:
    
    {
      "tech_debt": [
        { "id": 1, "descricao": "Código duplicado" }
      ]
    }
    

### 2.4 Regras Importantes para o MCP

- O campo `project_id` deve ser exatamente o mesmo recebido do backend na chamada de início de análise.
- O campo `report_type` DEVE ser igual ao tipo de relatório definido no mapeamento do backend para o `analysis_type` correspondente.
- O campo principal de `report_data` (ex: `epicos`, `features`, `tech_debt`) deve estar presente e conter a lista de resultados.
- Para status `error`, não envie `report_type` nem `report_data`.
- Para status `in_progress` e `done`, ambos `report_type` e `report_data` são obrigatórios.
- O backend rejeitará webhooks com estrutura inválida ou campos ausentes.
- O backend busca a sessão pelo project_id persistido no Redis. Se não encontrar, retorna 404 e loga o erro detalhadamente.

### 2.5 Exemplo de Webhook Inválido (Será Rejeitado)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_type": "epicos",
  "report_data": { 
    "errado": [
      { "id": 1, "titulo": "Como usuário..." }
    ]
  }
}

**Motivo:** O campo esperado em `report_data` para `report_type: "epicos"` é `epicos`, não `errado`.

### 2.6 Resumo do Mapeamento report_type → report_data

| analysis_type                  | report_type  | Campo principal em report_data |
|-------------------------------|--------------|-------------------------------|
| criacao_epicos_azure_devops    | epicos       | epicos_report                |
| refinamento_epicos_azure_devops| epicos       | epicos_report                        |

O MCP deve garantir que o campo principal de `report_data` corresponda ao mapeamento acima.

---

## 3. Exemplos de Respostas Backend → Frontend (Principais Endpoints)

### 3.1 /analysis/start
**Sucesso:**

{ 
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

**Erro:**

{ 
  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): Tempo limite excedido ao processar análise."
}

### 3.2 /session/{session_id}/reports
**Sucesso:**

{ 
  "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]},
  "features_report": { "features": [{ "id": 1, "nome": "Login" }]},
  "times_descricao_report": null,
  "alocacao_times_report": null,
  "premissas_riscos_report": null,
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

**Erro:**

{ 
  "detail": "Sessão não encontrada: ..."
}

### 3.3 /projects/check
**Projeto encontrado:**

{ 
  "exists": true,
  "state": { 
    "usuario_executor": "user@example.com",
    "projeto": "ProjetoNovo",
    "nome_projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]},
    "features_report": { "features": [{ "id": 1, "nome": "Login" }]},
    "times_descricao_report": null,
    "alocacao_times_report": null,
    "premissas_riscos_report": null,
    "docx_files": ["https://.../arquivo1.docx"],
    "comentario_usuario": "Comentário salvo",
    "extracted_text": "Texto extraído do arquivo DOCX da reunião",
    "project_id": "projeto-uuid-123"
  }
}

**Projeto não encontrado:**

{ 
  "exists": false
}

### 3.4 /auth/login
**Sucesso:**

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
      "nome_projeto": "ProjetoNovo",
      "analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "last_saved_to_blob": "2024-06-01T12:30:00Z",
      "project_id": "projeto-uuid-123"
    }
  ]
}

**Erro:**

{ 
  "detail": "Usuário não autenticado."
}

### 3.5 /upload/docx
**Sucesso:**

{ 
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "session_id": "ghijkl-uuid",
  "job_id": "ghijkl-uuid",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 3.6 /session/{session_id}/report (atualização de relatório)
**Sucesso:**

{ 
  "status": "ok",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

**Erro:**

{ 
  "detail": "Erro ao atualizar relatório: ..."
}

### 3.7 /session/{session_id}/save-state
**Sucesso:**

{ 
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/estados/estado_20240601T120000Z.json",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

**Erro:**

{ 
  "detail": "Erro ao salvar estado: ..."
}

### 3.8 /session/{session_id}/docx-files
**Sucesso:**

{ 
  "docx_files": [
    "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx"
  ],
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

**Erro:**

{ 
  "detail": "Sessão não encontrada: ..."
}

---

## 4. Exemplos de Respostas de Erro (Backend → Frontend)

| Código | Cenário | Exemplo |
|--------|---------|---------|
| 401 | Autenticação inválida | `{  "detail": "Cabeçalho Authorization ausente." }` |
| 403 | IP não autorizado | `{  "detail": "Acesso negado. IP 200.100.50.25 não autorizado." }` |
| 400 | Payload inválido | `{  "detail": "Os campos 'analysis_type' e pelo menos um de 'arquivo_docx' ou 'comentario_usuario' são obrigatórios." }` |
| 502 | Falha comunicação MCP | `{  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): ..." }` |
| 504 | Timeout MCP | `{  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): Tempo limite excedido ao processar análise." }` |
| 503 | Key Vault indisponível | `{  "detail": "Erro ao carregar segredos do Key Vault na inicialização: ..." }` |
| 503 | Redis indisponível | `{  "detail": "Erro ao conectar ao Redis (endpoint privado): ..." }` |
| 503 | Blob Storage indisponível | `{  "detail": "Erro ao conectar ao Blob Storage: ..." }` |
| 500 | Erro interno | `{  "detail": "Erro interno do servidor." }` |

---

## 5. Fluxo Completo de Comunicação (Exemplo End-to-End)

### 1. Login

POST /auth/login
Authorization: Bearer <token>

{}

Resposta:

{ 
  "user_info": { "usuario_executor": "user@example.com", "sub": "uuid", "name": "Nome do Usuário", "email": "user@example.com", "roles": ["admin"]},
  "projects": [{ "projeto": "ProjetoNovo", "nome_projeto": "ProjetoNovo", "analysis_type": "criacao_epicos_azure_devops", "created_at": "2024-06-01T12:00:00Z", "last_saved_to_blob": "2024-06-01T12:30:00Z", "project_id": "projeto-uuid-123"}]
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
    "nome_projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]},
    "features_report": { "features": [{ "id": 1, "nome": "Login" }]},
    "times_descricao_report": null,
    "alocacao_times_report": null,
    "premissas_riscos_report": null,
    "docx_files": ["https://.../arquivo1.docx"],
    "comentario_usuario": "Comentário salvo",
    "extracted_text": "Texto extraído do arquivo DOCX da reunião",
    "project_id": "projeto-uuid-123"
  }
}

### 3. Upload de DOCX

POST /upload/docx
Authorization: Bearer <token>
file=<arquivo.docx>&projeto=ProjetoNovo&analysis_type=criacao_epicos_azure_devops&comentario_usuario=Comentário opcional

Resposta:

{ 
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "session_id": "ghijkl-uuid",
  "job_id": "ghijkl-uuid",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 4. Início de Análise

POST /analysis/start
Authorization: Bearer <token>

{ 
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário."
}

Resposta:

{ 
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

> **Nota:** Toda a comunicação com o MCP utiliza o project_id como identificador principal. O job_id é apenas um identificador da execução no MCP, mas não é usado para buscar sessões no backend.

### 5. Webhook de Progresso (MCP → Backend)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "in_progress",
  "progress": 50,
  "report_type": "epicos",
  "report_data": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]}
}

### 6. Webhook de Conclusão (MCP → Backend)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_type": "epicos",
  "report_data": { "epicos": [{ "id": 1, "titulo": "Como usuário...", "descricao": "..." }]}
}

### 7. Consulta de Relatórios

GET /session/abcdef-uuid/reports
Authorization: Bearer <token>

Resposta:

{ 
  "epicos_report": { "epicos": [{ "id": 1, "titulo": "Como usuário..." }]},
  "features_report": { "features": [{ "id": 1, "nome": "Login" }]},
  "times_descricao_report": null,
  "alocacao_times_report": null,
  "premissas_riscos_report": null,
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 8. Salvamento Manual de Estado

POST /session/abcdef-uuid/save-state
Authorization: Bearer <token>

Resposta:

{ 
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/estados/estado_20240601T120000Z.json",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

---

## Notas
- Todos os exemplos de requisição (exceto `/auth/config`) exigem o header `Authorization: Bearer <token>`.
- O campo `project_id` está presente em todas as respostas de endpoints que envolvem projetos ou sessões.
- O campo `arquivo_docx` enviado para o MCP sempre contém o texto extraído do DOCX, nunca a URL.
- Todos os relatórios estão sob campos individuais (`epicos_report`, `features_report`, etc). Não existe mais a chave `reports`.
- O upload de DOCX retorna tanto a URL do arquivo quanto o texto extraído, em paralelo.
- Para erros, o backend sempre retorna o campo `detail` no corpo JSON.
- Toda a comunicação com o MCP utiliza o project_id como identificador principal. O job_id é apenas um identificador da execução no MCP, mas não é usado para buscar sessões no backend.
- O backend aceita o campo "projeto" (nome do projeto) do frontend, converte internamente para project_id, e responde sempre com ambos.
