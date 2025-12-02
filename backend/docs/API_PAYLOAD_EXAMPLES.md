# Exemplos de Payloads: Comunicação Frontend → Backend

Este documento apresenta exemplos práticos de payloads enviados pelo frontend para o backend Peers CodeAI, cobrindo os principais fluxos de uso, cenários comuns e casos de erro. Inclui exemplos de chamadas HTTP, headers, corpo da requisição e respostas esperadas.

---

## 1. Exemplos de Payloads por Cenário de Uso

### 1.1 Iniciar Análise - Três Formatos de Payload

**O campo `analysis_name` NÃO é mais utilizado.**

O backend aceita apenas um dos três formatos de payload abaixo (todos os campos obrigatórios, exceto onde indicado como opcional):

**Exemplo 1:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "<arquivo .docx>",
  "comentario_usuario": "Este é um comentário adicional do usuário."
}


**Exemplo 2:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "<arquivo .docx>"
}


**Exemplo 3:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_usuario": "Comentário sem arquivo."
}


**Resposta de Sucesso:**

{
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid"
}


---

### 1.2 Payload enviado do Backend para o MCP

O backend sempre envia para o MCP um dos três payloads abaixo, conforme o recebido do frontend:

**Exemplo 1:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo .docx",
  "comentario_usuario": "Este é um comentário adicional do usuário.",
  "usuario_executor": "user@example.com",
  "session_id": "abcdef-uuid"
}


**Exemplo 2:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "arquivo_docx": "Texto extraído do arquivo .docx",
  "usuario_executor": "user@example.com",
  "session_id": "abcdef-uuid"
}


**Exemplo 3:**

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_usuario": "Comentário sem arquivo.",
  "usuario_executor": "user@example.com",
  "session_id": "abcdef-uuid"
}


---

### 1.3 Upload de DOCX Adicional em Projeto Existente (Opcional)

**Endpoint:**
POST /upload/docx

**Headers:**
- Authorization: Bearer <token_jwt_azure_ad>
- Content-Type: multipart/form-data

**Form Data:**
- file: arquivo .docx
- projeto: "ProjetoExistente"
- analysis_type: "criacao_epicos_azure_devops"
- session_id: "ghijkl-uuid"
- is_new_project: false

**Resposta:**

{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise. (Upload opcional para projetos existentes)",
  "session_id": "ghijkl-uuid"
}


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

4. **Iniciar análise**
   - POST /analysis/start
   - Body: um dos três formatos acima

5. **Consulta de status/relatórios**
   - GET /session/{session_id}/reports

6. **Salvamento de estado**
   - POST /session/{session_id}/save-state

---

## 3. Casos de Erro Comuns

### 3.1 Token JWT inválido ou expirado

**Requisição:**
- Qualquer endpoint protegido
- Header: Authorization: Bearer <token_invalido>

**Resposta:**
HTTP 401

{
  "detail": "Usuário não autenticado."
}


---

### 3.2 Campos obrigatórios ausentes

**Exemplo:**
POST /analysis/start

{
  "projeto": "ProjetoNovo"
  // Faltando analysis_type e arquivo_docx/comentario_usuario
}

**Resposta:**
HTTP 400

{
  "detail": "Os campos 'analysis_type' e pelo menos um de 'arquivo_docx' ou 'comentario_usuario' são obrigatórios."
}


---

### 3.3 Projeto não encontrado

**Exemplo:**
GET /projects/check?projeto=ProjetoInexistente

**Resposta:**
HTTP 200

{
  "exists": false
}


---

### 3.4 Arquivo DOCX obrigatório não enviado para novo projeto

**Exemplo:**
POST /analysis/start

{
  "projeto": "ProjetoNovo",
  "analysis_type": "criacao_epicos_azure_devops"
  // Faltando arquivo_docx e comentario_usuario
}

**Resposta:**
HTTP 400

{
  "detail": "O upload do DOCX ou um comentário é obrigatório para novos projetos."
}


---

### 3.5 Erro de comunicação com MCP Server

**Exemplo:**
POST /analysis/start
- (Simule MCP Server offline)

**Resposta:**
HTTP 502

{
  "detail": "Erro ao comunicar com o servidor de Inteligência (MCP): ..."
}


---

### 3.6 Erro ao salvar no Blob Storage

**Exemplo:**
POST /session/{session_id}/save-state
- (Simule falha de conexão com Blob Storage)

**Resposta:**
HTTP 500

{
  "detail": "Erro ao salvar estado: ..."
}


---

### 3.7 Erro ao conectar ao Redis

**Exemplo:**
GET /session/{session_id}/reports
- (Simule falha de conexão Redis)

**Resposta:**
HTTP 404

{
  "detail": "Sessão não encontrada: ..."
}


---

### 3.8 IP não autorizado

**Exemplo:**
- Qualquer endpoint acessado de IP não permitido

**Resposta:**
HTTP 403

{
  "detail": "Acesso negado. IP <ip> não autorizado."
}


---

## Observações Gerais
- O campo `analysis_name` foi removido de todos os fluxos.
- O campo opcional `comentario_usuario` pode ser enviado tanto no upload do DOCX quanto na solicitação de análise.
- O campo `arquivo_docx` é obrigatório apenas se não houver `comentario_usuario`.
- Para projetos existentes, basta informar o nome do projeto e o tipo de análise, com pelo menos um dos campos opcionais.
- O header Authorization é obrigatório para todos os endpoints protegidos.
- Todos os exemplos de resposta seguem o padrão JSON.
