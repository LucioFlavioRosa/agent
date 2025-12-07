# Exemplos de Payloads: Comunicação Frontend ↔ Backend ↔ MCP

Este documento apresenta exemplos práticos de payloads enviados pelo frontend para o backend Peers CodeAI, exemplos de respostas do backend para o frontend, exemplos de respostas do MCP para o backend, e o fluxo completo de comunicação. Inclui exemplos de chamadas HTTP, headers, corpo da requisição e respostas esperadas.

---

## 1. Exemplos de Payloads por Cenário de Uso

### 1.1 Login (POST /auth/login)

POST /auth/login HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

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

GET /projects/check?nome_projeto=ProjetoNovo HTTP/1.1
Authorization: Bearer <token>

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

{ "exists": false }

### 1.3 Início de Análise (POST /analysis/start)

POST /analysis/start HTTP/1.1
Authorization: Bearer <token>
Content-Type: multipart/form-data

nome_projeto=ProjetoNovo
analysis_type=criacao_epicos_azure_devops
instrucoes_extras=Este é um comentário adicional do usuário.
arquivo_docx=<arquivo.docx>

- O campo `arquivo_docx` deve ser enviado como arquivo via multipart/form-data.
- O backend irá extrair o texto do arquivo e salvá-lo no Blob Storage em paralelo.
- O texto extraído será enviado ao MCP no campo `arquivo_docx` do payload.
- Se `arquivo_docx` não for fornecido, é obrigatório informar `instrucoes_extras`.

**Resposta:**

{ 
  "message": "Análise solicitada com sucesso ao agente.",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.4 Atualização de Relatório (PUT /session/project/{project_id}/report)

PUT /session/project/projeto-uuid-123/report HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{ 
  "report_data": { "features_report": [{ "id": 101, "nome": "Configurar App Registration Azure", "descricao": "Criar app no entra ID" }] }
}

{ 
  "status": "ok",
  "project_id": "projeto-uuid-123",
  "nome_projeto": "ProjetoNovo"
}

### 1.5 Consulta de Relatórios (GET /session/project/{project_id}/reports)

GET /session/project/projeto-uuid-123/reports HTTP/1.1
Authorization: Bearer <token>

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

POST /webhooks/mcp
Content-Type: application/json

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

{ 
  "job_id": "123456",
  "project_id": "projeto-uuid-123",
  "status": "error",
  "error_type": "timeout",
  "error_message": "Tempo limite excedido ao processar análise."
}

---

## Notas
- O endpoint /upload/docx foi removido. O upload de arquivo DOCX e a extração de texto ocorrem exclusivamente via POST /analysis/start.
- O campo `arquivo_docx` enviado para o MCP sempre contém o texto extraído do DOCX, nunca a URL.
- Para iniciar análise, é obrigatório informar `analysis_type` e pelo menos um de `arquivo_docx` (arquivo) ou `instrucoes_extras`.
- O backend salva o arquivo DOCX no Blob Storage em paralelo ao processamento.
- O campo `project_id` está presente em todas as respostas de endpoints que envolvem projetos ou sessões.
- Todos os relatórios estão sob campos individuais (`epicos_report`, `features_report`, etc). Não existe mais a chave `reports` ou campos obsoletos no estado do projeto.
- Toda a comunicação com o MCP utiliza o project_id como identificador principal.
