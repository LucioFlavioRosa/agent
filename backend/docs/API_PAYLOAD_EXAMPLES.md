# Exemplos de Payloads: Comunicação Frontend → Backend → MCP → Backend → Frontend

Este documento apresenta exemplos práticos de payloads enviados pelo frontend para o backend Peers CodeAI, exemplos de respostas do backend para o frontend, exemplos de respostas do MCP para o backend, e o fluxo completo de comunicação. Inclui exemplos de chamadas HTTP, headers, corpo da requisição e respostas esperadas.

---

## 1. Exemplos de Payloads por Cenário de Uso

### 1.1 Iniciar Análise - Três Formatos de Payload (Frontend → Backend)

**O campo `analysis_name` NÃO é mais utilizado.**

O backend aceita apenas um dos três formatos de payload abaixo (todos os campos obrigatórios, exceto onde indicado como opcional):

**Exemplo 1:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário."
}

**Exemplo 2:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião"
}

**Exemplo 3:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_usuario": "Comentário sem arquivo."
}

---

### 1.2 Resposta do Backend para o Frontend (Backend → Frontend)

#### /analysis/start
**Resposta de Sucesso:**

{
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid",
  "project_id": "projeto-uuid-123"
}

**Resposta de Erro:**

{
  "detail": "Os campos 'analysis_type' e pelo menos um de 'arquivo_docx' ou 'comentario_usuario' são obrigatórios."
}

#### /session/{session_id}/reports
**Resposta de Sucesso:**

{
  "epicos_report": {"epicos": [{"id": 1, "titulo": "Como usuário..."}]},
  "features_report": {"features": [{"id": 1, "nome": "Login"}]},
  "times_descricao_report": {},
  "alocacao_times_report": {},
  "premissas_riscos_report": {}
}

**Resposta de Erro:**

{
  "detail": "Sessão não encontrada: ..."
}

#### /projects/check
**Projeto encontrado:**

{
  "exists": true,
  "state": {
    "usuario_executor": "user@example.com",
    "projeto": "ProjetoNovo",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": {"epicos": [{"id": 1, "titulo": "Como usuário..."}]},
    "features_report": {"features": [{"id": 1, "nome": "Login"}]},
    "times_descricao_report": {},
    "alocacao_times_report": {},
    "premissas_riscos_report": {},
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

#### /auth/login
**Resposta de Sucesso:**

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

**Resposta de Erro:**

{
  "detail": "Usuário não autenticado."
}

#### /upload/docx
**Resposta de Sucesso:**

{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "session_id": "ghijkl-uuid"
}

#### /session/{session_id}/report (atualização de relatório)
**Resposta de Sucesso:**

{
  "status": "ok"
}

**Resposta de Erro:**

{
  "detail": "Erro ao atualizar relatório: ..."
}

#### /session/{session_id}/save-state (salvamento de estado)
**Resposta de Sucesso:**

{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/estados/estado_20240601T120000Z.json"
}

**Resposta de Erro:**

{
  "detail": "Erro ao salvar estado: ..."
}

#### /session/{session_id}/docx-files
**Resposta de Sucesso:**

{
  "docx_files": [
    "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx"
  ]
}

**Resposta de Erro:**

{
  "detail": "Sessão não encontrada: ..."
}

---

## 2. Exemplos de Respostas MCP → Backend

### 2.1 Resposta de Sucesso (job criado)

{
  "job_id": "123456"
}

- O campo "arquivo_docx" enviado para o MCP sempre contém o texto extraído do DOCX, nunca a URL do arquivo.

### 2.2 Notificação de Progresso (webhook MCP → Backend)

{
  "job_id": "123456",
  "status": "in_progress",
  "progress": 50,
  "report_type": "epicos",
  "report_data": {
    "epicos": [
      {"id": 1, "titulo": "Como usuário...", "descricao": "..."}
    ]
  }
}

### 2.3 Resposta de Conclusão

{
  "job_id": "123456",
  "status": "done",
  "report_type": "epicos",
  "report_data": {
    "epicos": [
      {"id": 1, "titulo": "Como usuário...", "descricao": "..."},
      {"id": 2, "titulo": "Como admin...", "descricao": "..."}
    ]
  }
}

### 2.4 Resposta de Erro (MCP → Backend)

{
  "job_id": "123456",
  "status": "error",
  "error_type": "timeout",
  "error_message": "Tempo limite excedido ao processar análise."
}

### 2.5 Exemplo para analysis_type diferente

{
  "job_id": "7891011",
  "status": "done",
  "report_type": "features",
  "report_data": {
    "features": [
      {"id": 1, "nome": "Login", "descricao": "Permitir login com Azure AD"}
    ]
  }
}

---

## 3. Exemplos de Respostas Backend → Frontend (todos endpoints principais)

### 3.1 /analysis/start
**Sucesso:**

{
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid",
  "project_id": "projeto-uuid-123"
}

**Erro:**

{
  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): Tempo limite excedido ao processar análise."
}

### 3.2 /session/{session_id}/reports
**Sucesso:**

{
  "epicos_report": {"epicos": [{"id": 1, "titulo": "Como usuário..."}]},
  "features_report": {"features": [{"id": 1, "nome": "Login"}]},
  "times_descricao_report": {},
  "alocacao_times_report": {},
  "premissas_riscos_report": {}
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
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:00:00Z",
    "last_saved_to_blob": "2024-06-01T12:30:00Z",
    "epicos_report": {"epicos": [{"id": 1, "titulo": "Como usuário..."}]},
    "features_report": {"features": [{"id": 1, "nome": "Login"}]},
    "times_descricao_report": {},
    "alocacao_times_report": {},
    "premissas_riscos_report": {},
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
  "session_id": "ghijkl-uuid"
}

### 3.6 /session/{session_id}/report (atualização de relatório)
**Sucesso:**

{
  "status": "ok"
}

**Erro:**

{
  "detail": "Erro ao atualizar relatório: ..."
}

### 3.7 /session/{session_id}/save-state (salvamento de estado)
**Sucesso:**

{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/estados/estado_20240601T120000Z.json"
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
  ]
}

**Erro:**

{
  "detail": "Sessão não encontrada: ..."
}

---

## 4. Fluxo Completo de Comunicação

**1. Frontend → Backend**
- Payload enviado para `/analysis/start`:

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário."
}

**2. Backend → MCP**
- Payload enviado do backend para o MCP:

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário.",
  "usuario_executor": "user@example.com",
  "session_id": "abcdef-uuid"
}

**3. MCP → Backend**
- Resposta do MCP ao backend (job criado):

{
  "job_id": "123456"
}

- Resposta de progresso ou conclusão:

{
  "job_id": "123456",
  "status": "done",
  "report_type": "epicos",
  "report_data": {
    "epicos": [
      {"id": 1, "titulo": "Como usuário...", "descricao": "..."}
    ]
  }
}

**4. Backend → Frontend**
- Resposta do backend para o frontend:

{
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid",
  "project_id": "projeto-uuid-123"
}

**Diagrama Textual do Fluxo:**
1. Frontend envia requisição para Backend (`/analysis/start`)
2. Backend processa, salva sessão, envia payload para MCP (com texto extraído do DOCX)
3. MCP responde com `job_id` e posteriormente envia progresso/resultado
4. Backend atualiza sessão/relatórios e responde ao Frontend

---

## 5. Exemplos de Respostas do MCP para Diferentes analysis_type

### Para `criacao_epicos_azure_devops`

{
  "job_id": "123456",
  "status": "done",
  "report_type": "epicos",
  "report_data": {
    "epicos": [
      {"id": 1, "titulo": "Como usuário...", "descricao": "..."},
      {"id": 2, "titulo": "Como admin...", "descricao": "..."}
    ]
  }
}

### Para `features_generation` (exemplo futuro)

{
  "job_id": "7891011",
  "status": "done",
  "report_type": "features",
  "report_data": {
    "features": [
      {"id": 1, "nome": "Login", "descricao": "Permitir login com Azure AD"}
    ]
  }
}

---

## 6. Exemplos de Respostas de Erro do MCP e Propagação para o Frontend

### MCP retorna erro (exemplo: timeout)

{
  "job_id": "123456",
  "status": "error",
  "error_type": "timeout",
  "error_message": "Tempo limite excedido ao processar análise."
}

### Backend propaga erro para o frontend

{
  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): Tempo limite excedido ao processar análise."
}

---

## 7. Observações Gerais
- O campo `analysis_name` foi removido de todos os fluxos.
- O campo opcional `comentario_usuario` pode ser enviado tanto no upload do DOCX quanto na solicitação de análise.
- O campo `arquivo_docx` é obrigatório apenas se não houver `comentario_usuario`.
- Para projetos existentes, basta informar o nome do projeto e o tipo de análise, com pelo menos um dos campos opcionais.
- O header Authorization é obrigatório para todos os endpoints protegidos.
- Todos os exemplos de resposta seguem o padrão JSON.
- O campo "arquivo_docx" enviado para o MCP sempre contém o texto extraído do DOCX, nunca a URL do arquivo.
- O campo `project_id` agora é retornado em todas as respostas de endpoints que envolvem projetos ou sessões.
- O upload de DOCX retorna tanto a URL do arquivo quanto o texto extraído, em paralelo.
