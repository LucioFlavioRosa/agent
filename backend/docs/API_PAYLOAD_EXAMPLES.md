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

GET /projects/check?nome_projeto=ProjetoNovo HTTP/1.1
Authorization: Bearer <token>

**Resposta (projeto encontrado):**

{ 
  "exists": true,
  "state": { 
    "usuario_executor": "user@example.com",
    "nome_projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": [{ "id": 1, "titulo": "Como usuário..." }],
    "features_report": [{ "id": 1, "nome": "Login" }],
    "times_descricao_report": null,
    "alocacao_times_report": null,
    "premissas_riscos_report": null,
    "docx_files": ["https://.../arquivo1.docx"],
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
nome_projeto=ProjetoNovo
analysis_type=criacao_epicos_azure_devops
instrucoes_extras=Comentário opcional

**Resposta:**

{ 
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.4 Início de Análise (POST /analysis/start)

**Requisição (projeto novo):**

POST /analysis/start HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{ 
  "nome_projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "instrucoes_extras": "Este é um comentário adicional do usuário.",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião"
}

**Fluxo interno:**
- O backend recebe o campo "nome_projeto" do frontend.
- O backend busca o project_id correspondente ao nome do projeto (se existir); caso contrário, gera um novo project_id.
- Todas as operações internas e comunicação com o MCP passam a usar project_id como identificador principal.
- O backend pode enviar nome_projeto na resposta para exibição no frontend.

**Payload enviado do backend para o MCP:**

{
  "project_id": "projeto-uuid-123",
  "analysis_type": "criacao_epicos_azure_devops",
  "instrucoes_extras": "Este é um comentário adicional do usuário.",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião"
}

> **Nota:** O campo project_id é sempre utilizado como identificador principal na comunicação com o MCP. O campo nome_projeto é enviado apenas para log/debug.

**Resposta:**

{ 
  "message": "Análise solicitada com sucesso ao agente.",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.5 Atualização de Relatório (PUT /session/project/{project_id}/report)

**Requisição:**

PUT /session/project/projeto-uuid-123/report HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{ 
  "report_data": { "features_report": [{ "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" }] }
}

**Resposta:**

{ 
  "status": "ok",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.6 Consulta de Relatórios (GET /session/project/{project_id}/reports)

**Requisição:**

GET /session/project/projeto-uuid-123/reports HTTP/1.1
Authorization: Bearer <token>

**Resposta:**

{ 
  "epicos_report": [{ "id": 1, "titulo": "Como usuário..." }],
  "features_report": [{ "id": 1, "nome": "Login" }],
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
  "report_data": { "features_report": [{ ... }] },
  "error_type": <string, obrigatório quando status="error">,
  "error_message": <string, obrigatório quando status="error">
}

**Campos obrigatórios:**
- `job_id`: string. Identificador do job retornado pelo backend ao MCP.
- `project_id`: string. Identificador único do projeto, usado para buscar a sessão correspondente.
- `status`: string. Um dos valores: `in_progress`, `done`, `error`.
- `progress`: inteiro opcional (0-100), só para status `in_progress`.
- `report_data`: objeto/dict. Obrigatório para status `in_progress` ou `done`. Estrutura: `{<report_field>: [ ... ]}`. Exemplo: `{ "features_report": [{ ... }] }`
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
  "report_data": { 
    "features_report": [
      { "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" }
    ]
  }
}

#### 2.2.2 Webhook de Conclusão (`status: done`)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_data": { 
    "features_report": [
      { "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" },
      { "id": 102, "nome": "Middleware de Validação JWT", "descricao": "Validar token no backend Python" }
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

### 2.3 Estrutura de report_data Esperada por Tipo

- Para `features_report`:
    { "features_report": [ { ... } ] }
- Para `epicos_report`:
    { "epicos_report": [ { ... } ] }
- Para `times_descricao_report`:
    { "times_descricao_report": [ { ... } ] }
- Para `alocacao_times_report`:
    { "alocacao_times_report": [ { ... } ] }
- Para `premissas_riscos_report`:
    { "premissas_riscos_report": [ { ... } ] }

> O backend irá atualizar apenas o campo correspondente no estado do projeto.

### 2.4 Regras Importantes para o MCP

- O campo `project_id` deve ser exatamente o mesmo recebido do backend na chamada de início de análise.
- O campo principal de `report_data` (ex: `features_report`, `epicos_report`, etc) deve estar presente e conter a lista de resultados.
- Para status `error`, não envie `report_data`.
- Para status `in_progress` e `done`, `report_data` é obrigatório e deve conter exatamente uma chave de relatório.
- O backend rejeitará webhooks com estrutura inválida ou campos ausentes.
- O backend busca a sessão pelo project_id persistido no Redis. Se não encontrar, retorna 404 e loga o erro detalhadamente.

### 2.5 Exemplo de Webhook Inválido (Será Rejeitado)

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "done",
  "report_data": { 
    "errado": [
      { "id": 1, "titulo": "Como usuário..." }
    ]
  }
}

**Motivo:** O campo esperado em `report_data` deve ser um dos: `epicos_report`, `features_report`, `times_descricao_report`, `alocacao_times_report`, `premissas_riscos_report`.

### 2.6 Resumo dos Campos de Relatório Aceitos

| Campo em report_data           |
|-------------------------------|
| epicos_report                 |
| features_report               |
| times_descricao_report        |
| alocacao_times_report         |
| premissas_riscos_report       |

---

## 3. Exemplos de Respostas Backend → Frontend (Principais Endpoints)

### 3.1 /analysis/start
**Sucesso:**

{ 
  "message": "Análise solicitada com sucesso ao agente.",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

**Erro:**

{ 
  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): Tempo limite excedido ao processar análise."
}

### 3.2 /session/project/{project_id}/reports
**Sucesso:**

{ 
  "epicos_report": [{ "id": 1, "titulo": "Como usuário..." }],
  "features_report": [{ "id": 1, "nome": "Login" }],
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
    "nome_projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": [{ "id": 1, "titulo": "Como usuário..." }],
    "features_report": [{ "id": 1, "nome": "Login" }],
    "times_descricao_report": null,
    "alocacao_times_report": null,
    "premissas_riscos_report": null,
    "docx_files": ["https://.../arquivo1.docx"],
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
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 3.6 /session/project/{project_id}/report (atualização de relatório)
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

### 3.7 /session/project/{project_id}/save-state
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

### 3.8 /session/project/{project_id}/docx-files
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

## Notas
- Todos os exemplos de requisição (exceto `/auth/config`) exigem o header `Authorization: Bearer <token>`.
- O campo `project_id` está presente em todas as respostas de endpoints que envolvem projetos ou sessões.
- O campo `arquivo_docx` enviado para o MCP sempre contém o texto extraído do DOCX, nunca a URL.
- Todos os relatórios estão sob campos individuais (`epicos_report`, `features_report`, etc). Não existe mais a chave `reports` ou campos obsoletos no estado do projeto.
- O upload de DOCX retorna tanto a URL do arquivo quanto o texto extraído, em paralelo.
- Para erros, o backend sempre retorna o campo `detail` no corpo JSON.
- Toda a comunicação com o MCP utiliza o project_id como identificador principal. O job_id é apenas um identificador da execução no MCP, mas não é usado para buscar sessões no backend.
- O backend aceita o campo "nome_projeto" do frontend, converte internamente para project_id, e responde sempre com ambos.
