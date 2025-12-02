# Exemplos de Payloads: /analysis/start

## 1. Iniciar Análise com DOCX (Novo Projeto)

**Requisição:**
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
```
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

## 2a. Iniciar Análise em Projeto Existente informando apenas o nome do projeto

**Requisição:**
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
  "analysis_type": "criacao_epicos_azure_devops",
  "comentario_usuario": "Comentário para projeto inexistente."
}
```
**Resposta de Erro:**
```json
{
  "detail": "O upload do DOCX é obrigatório para novos projetos."
}
```
---

## 4. Upload de DOCX com comentário do usuário

**Endpoint:**
POST /upload/docx

**Payload Form Data:**
- file: arquivo .docx
- projeto: "ProjetoNovo"
- analysis_name: "Sprint 1"
- analysis_type: "criacao_epicos_azure_devops"
- comentario_usuario: "Comentário do usuário para upload."

**Resposta:**
```json
{
  "blob_url": "https://storage.blob.core.windows.net/usuario/projeto/arquivos_recebidos/docx/Sprint1.docx",
  "extracted_text": "Texto extraído do DOCX da reunião",
  "message": "Arquivo processado com sucesso. Pronto para análise.",
  "session_id": "abcdef-uuid"
}
```
---

## 5. Consultar arquivos DOCX enviados para uma sessão

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

## 6. Verificar existência de projeto antes de qualquer operação

**Endpoint:**
GET /projects/check?projeto=ProjetoExistente

**Exemplo de requisição:**
GET /projects/check?projeto=ProjetoExistente

**Exemplo de resposta para projeto existente:**
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
**Exemplo de resposta para projeto inexistente:**
```json
{
  "exists": false
}
```
---

## Observações
- O frontend deve sempre chamar `/projects/check` antes de qualquer outra operação (upload, análise) para garantir que o projeto existe e obter o último estado salvo.
- O campo `extracted_text` só é obrigatório se o projeto não existir previamente para o usuário.
- Para projetos existentes, basta informar o nome do projeto. O backend irá buscar o usuário autenticado e os metadados necessários (`analysis_name` e `analysis_type`) automaticamente do estado mais recente no Blob Storage.
- O campo opcional `comentario_usuario` pode ser enviado tanto no upload do DOCX quanto na solicitação de análise, e será propagado para o MCP Server.
- O backend faz a verificação automática do estado do projeto no Blob Storage.
- Todo arquivo DOCX enviado tem seu caminho salvo no campo `docx_files` do estado da sessão, permitindo rastreabilidade e recuperação de todas as histórias geradas.
- O endpoint `GET /session/{session_id}/docx-files` retorna o histórico completo de arquivos DOCX enviados para a sessão.
