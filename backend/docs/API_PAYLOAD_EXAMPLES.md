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


---

### 1.2 Resposta do Backend para o Frontend (Backend → Frontend)

#### /auth/login
**Requisição:**

POST /auth/login
Authorization: Bearer <token>
Content-Type: application/json

(não enviar corpo de requisição)


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
      "last_saved_to_blob": "2024-06-01T12:30:00Z"
    }
  ]
}


**Resposta de Erro:**

{
  "detail": "Usuário não autenticado."
}


---

(Os demais exemplos de payload e respostas permanecem conforme as seções anteriores)
