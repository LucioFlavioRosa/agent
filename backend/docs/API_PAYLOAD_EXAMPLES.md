# Exemplos de Payloads: /analysis/start

## 1. Iniciar Análise com DOCX (Novo Projeto)

**Requisição:**
```json
{
  "projeto": "ProjetoNovo",
  "analysis_name": "Sprint 1",
  "analysis_type": "criacao_epicos_azure_devops",
  "extracted_text": "Texto extraído do DOCX da reunião"
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

**Resposta de Erro (faltando DOCX para novo projeto):**
```json
{
  "detail": "O upload do DOCX é obrigatório para novos projetos."
}
```

---

## 2. Iniciar Análise sem DOCX (Projeto Existente)

**Requisição:**
```json
{
  "projeto": "ProjetoExistente",
  "analysis_name": "Sprint 2",
  "analysis_type": "criacao_epicos_azure_devops"
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

## 2a. Iniciar Análise em Projeto Existente informando apenas o nome do projeto

**Requisição:**
```json
{
  "projeto": "ProjetoExistente"
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

**Resposta de Erro (projeto não encontrado):**
```json
{
  "detail": "Projeto não encontrado para o usuário informado."
}
```

---

## 3. Iniciar Análise sem DOCX para Projeto Inexistente (Erro)

**Requisição:**
```json
{
  "projeto": "ProjetoInexistente",
  "analysis_name": "Sprint 3",
  "analysis_type": "criacao_epicos_azure_devops"
}
```

**Resposta de Erro:**
```json
{
  "detail": "O upload do DOCX é obrigatório para novos projetos."
}
```

---

## 4. Consultar arquivos DOCX enviados para uma sessão

**Endpoint:**

GET /session/{session_id}/docx-files

**Exemplo de resposta com lista vazia:**
```json
{
  "docx_files": []
}
```

**Exemplo de resposta com múltiplos arquivos:**
```json
{
  "docx_files": [
    "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint1.docx",
    "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint2.docx"
  ]
}
```

---

## Observações
- O campo `extracted_text` só é obrigatório se o projeto não existir previamente para o usuário.
- Para projetos existentes, basta informar o nome do projeto. O backend irá buscar o usuário autenticado e os metadados necessários (`analysis_name` e `analysis_type`) automaticamente do estado mais recente no Blob Storage.
- O backend faz a verificação automática do estado do projeto no Blob Storage.
- Todo arquivo DOCX enviado tem seu caminho salvo no campo `docx_files` do estado da sessão, permitindo rastreabilidade e recuperação de todas as histórias geradas.
- O endpoint `GET /session/{session_id}/docx-files` retorna o histórico completo de arquivos DOCX enviados para a sessão.
