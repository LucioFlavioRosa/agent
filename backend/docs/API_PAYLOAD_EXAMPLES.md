# Exemplos de Payloads: Comunicação Frontend → Backend

Este documento apresenta exemplos práticos de payloads enviados pelo frontend para o backend Peers CodeAI, cobrindo os principais fluxos de uso, cenários comuns e casos de erro. Inclui exemplos de chamadas HTTP, headers, corpo da requisição e respostas esperadas.

---

## 1. Exemplos de Payloads por Cenário de Uso

### 1.1 Iniciar Análise com DOCX e Comentário em Projeto Novo

**Endpoint:**
POST /analysis/start

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>
- Content-Type: application/json

**Body:**
```json
{
  "projeto": "ProjetoNovo",
  "analysis_name": "Sprint 1",
  "analysis_type": "criacao_epicos_azure_devops",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "comentario_usuario": "Este é um comentário adicional do usuário."
}
```
**Resposta de Sucesso:**
```json
{
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid"
}
```

---

### 1.2 Iniciar Análise em Projeto Existente apenas com Nome do Projeto

**Endpoint:**
POST /analysis/start

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>
- Content-Type: application/json

**Body:**
```json
{
  "projeto": "ProjetoExistente",
  "comentario_usuario": "Comentário para análise apenas com nome do projeto."
}
```
**Resposta de Sucesso:**
```json
{
  "job_id": "789012",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "ghijkl-uuid"
}
```

---

### 1.3 Iniciar Análise em Projeto Existente informando analysis_name e analysis_type

**Endpoint:**
POST /analysis/start

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>
- Content-Type: application/json

**Body:**
```json
{
  "projeto": "ProjetoExistente",
  "analysis_name": "Sprint 2",
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_usuario": "Comentário para análise existente."
}
```
**Resposta de Sucesso:**
```json
{
  "job_id": "789012",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "ghijkl-uuid"
}
```

---

### 1.4 Upload de DOCX Adicional em Projeto Existente

**Endpoint:**
POST /upload/docx

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>
- Content-Type: multipart/form-data

**Form Data:**
- file: arquivo .docx
- projeto: "ProjetoExistente"
- analysis_name: "Sprint 2"
- session_id: "ghijkl-uuid"
- is_new_project: false

**Resposta:**
```json
{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "session_id": "ghijkl-uuid"
}
```

---

### 1.5 Consulta de Relatórios de Sessão

**Endpoint:**
GET /session/{session_id}/reports

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>

**Resposta:**
```json
{
  "epicos_report": {...},
  "features_report": {...},
  "times_descricao_report": {...},
  "alocacao_times_report": {...},
  "premissas_riscos_report": {...}
}
```

---

### 1.6 Atualização de Relatório Específico

**Endpoint:**
PUT /session/{session_id}/report

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>
- Content-Type: application/json

**Body:**
```json
{
  "report_type": "epicos",
  "report_data": { "campo": "valor" }
}
```
**Resposta:**
```json
{
  "status": "ok"
}
```

---

### 1.7 Salvamento Manual de Estado da Sessão

**Endpoint:**
POST /session/{session_id}/save-state

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>

**Resposta:**
```json
{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/estados/estado_20240601T130000Z.json"
}
```

---

### 1.8 Verificação de Projeto com Resposta de Estado Completo

**Endpoint:**
GET /projects/check?projeto=ProjetoExistente

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>

**Resposta para projeto existente:**
```json
{
  "exists": true,
  "state": {
    "usuario_executor": "user@example.com",
    "projeto": "ProjetoExistente",
    "analysis_name": "Sprint 2",
    "analysis_type": "criacao_epicos_azure_devops",
    "created_at": "2024-06-01T12:34:56Z",
    "last_saved_to_blob": "2024-06-01T13:00:00Z",
    "epicos_report": null,
    "features_report": null,
    "times_descricao_report": null,
    "alocacao_times_report": null,
    "premissas_riscos_report": null,
    "docx_files": ["https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx"],
    "comentario_usuario": "Comentário salvo no estado."
  }
}
```
**Resposta para projeto inexistente:**
```json
{
  "exists": false
}
```

---

### 1.9 Listagem de Projetos após Login

**Endpoint:**
POST /auth/login

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>

**Resposta:**
```json
{
  "user_info": {
    "sub": "user-teste-id-123",
    "usuario_executor": "dev_tester_local",
    "name": "Desenvolvedor Teste",
    "email": "dev@peers.com.br",
    "roles": ["admin"]
  },
  "projects": [
    {
      "projeto": "ProjetoExistente",
      "analysis_name": "Sprint 2",
      "analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:34:56Z",
      "last_saved_to_blob": "2024-06-01T13:00:00Z"
    },
    {
      "projeto": "ProjetoNovo",
      "analysis_name": "Sprint 1",
      "analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-02T09:00:00Z",
      "last_saved_to_blob": "2024-06-02T09:30:00Z"
    }
  ]
}
```

---

## 2. Fluxo Completo de Uso (Sequência Típica de Chamadas)

1. **Login e obtenção do token JWT Azure AD**
   - O frontend autentica o usuário e obtém o token via Azure AD/MSAL.

2. **Listagem de projetos do usuário**
   - POST /auth/login
   - Header: Authorization: Bearer <token>

3. **Verificação de projeto existente**
   - GET /projects/check?projeto=ProjetoX
   - Header: Authorization: Bearer <token>

4. **Upload de DOCX (se novo projeto)**
   - POST /upload/docx
   - FormData: file, projeto, analysis_name, analysis_type, comentario_usuario

5. **Iniciar análise**
   - POST /analysis/start
   - Body: conforme exemplos acima

6. **Consulta de status/relatórios**
   - GET /session/{session_id}/reports

7. **Salvamento de estado**
   - POST /session/{session_id}/save-state

---

## 3. Casos de Erro Comuns

### 3.1 Token JWT inválido ou expirado

**Requisição:**
- Qualquer endpoint protegido
- Header: Authorization: Bearer <token_invalido>

**Resposta:**
HTTP 401
```json
{
  "detail": "Usuário não autenticado."
}
```

---

### 3.2 Campos obrigatórios ausentes

**Exemplo:**
POST /analysis/start
```json
{
  "projeto": "ProjetoNovo"
  // Faltando analysis_name, analysis_type e extracted_text
}
```
**Resposta:**
HTTP 400
```json
{
  "detail": "Os campos 'analysis_name' e 'analysis_type' são obrigatórios para novos projetos."
}
```

---

### 3.3 Projeto não encontrado

**Exemplo:**
GET /projects/check?projeto=ProjetoInexistente

**Resposta:**
HTTP 200
```json
{
  "exists": false
}
```

---

### 3.4 Arquivo DOCX obrigatório não enviado para novo projeto

**Exemplo:**
POST /analysis/start
```json
{
  "projeto": "ProjetoNovo",
  "analysis_name": "Sprint 1",
  "analysis_type": "criacao_epicos_azure_devops"
  // Faltando extracted_text
}
```
**Resposta:**
HTTP 400
```json
{
  "detail": "O upload do DOCX é obrigatório para novos projetos."
}
```

---

### 3.5 Erro de comunicação com MCP Server

**Exemplo:**
POST /analysis/start
- (Simule MCP Server offline)

**Resposta:**
HTTP 502
```json
{
  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): ..."
}
```

---

### 3.6 Erro ao salvar no Blob Storage

**Exemplo:**
POST /session/{session_id}/save-state
- (Simule falha de conexão com Blob Storage)

**Resposta:**
HTTP 500
```json
{
  "detail": "Erro ao salvar estado: ..."
}
```

---

### 3.7 Erro ao conectar ao Redis

**Exemplo:**
GET /session/{session_id}/reports
- (Simule falha de conexão Redis)

**Resposta:**
HTTP 404
```json
{
  "detail": "Sessão não encontrada: ..."
}
```

---

### 3.8 IP não autorizado

**Exemplo:**
- Qualquer endpoint acessado de IP não permitido

**Resposta:**
HTTP 403
```json
{
  "detail": "Acesso negado. IP <ip> não autorizado."
}
```

---

## Observações Gerais
- O campo opcional `comentario_usuario` pode ser enviado tanto no upload do DOCX quanto na solicitação de análise.
- O campo `extracted_text` é obrigatório apenas para novos projetos.
- Para projetos existentes, basta informar o nome do projeto ou, opcionalmente, analysis_name e analysis_type.
- O header Authorization é obrigatório para todos os endpoints protegidos.
- Todos os exemplos de resposta seguem o padrão JSON.
