# Exemplos de Payloads: /analysis/start

## 1. Iniciar Análise com DOCX (Novo Projeto)

**Requisição:**

{
  "projeto": "ProjetoNovo",
  "analysis_name": "Sprint 1",
  "analysis_type": "criacao_epicos_azure_devops",
  "extracted_text": "Texto extraído do DOCX da reunião"
}


**Resposta de Sucesso:**

{
  "job_id": "123456",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "abcdef-uuid"
}


**Resposta de Erro (faltando DOCX para novo projeto):**

{
  "detail": "O upload do DOCX é obrigatório para novos projetos."
}


---

## 2. Iniciar Análise sem DOCX (Projeto Existente)

**Requisição:**

{
  "projeto": "ProjetoExistente",
  "analysis_name": "Sprint 2",
  "analysis_type": "criacao_epicos_azure_devops"
}


**Resposta de Sucesso:**

{
  "job_id": "789012",
  "message": "Análise solicitada com sucesso ao agente.",
  "session_id": "ghijkl-uuid"
}


---

## 3. Iniciar Análise sem DOCX para Projeto Inexistente (Erro)

**Requisição:**

{
  "projeto": "ProjetoInexistente",
  "analysis_name": "Sprint 3",
  "analysis_type": "criacao_epicos_azure_devops"
}


**Resposta de Erro:**

{
  "detail": "O upload do DOCX é obrigatório para novos projetos."
}


---

## Observações
- O campo `extracted_text` só é obrigatório se o projeto não existir previamente para o usuário.
- Para projetos existentes, basta informar o nome do projeto, analysis_name e analysis_type.
- O backend faz a verificação automática do estado do projeto no Blob Storage.
