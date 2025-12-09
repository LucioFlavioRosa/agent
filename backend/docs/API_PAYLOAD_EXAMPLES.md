# Índice

- [1. Introdução](#1-introdução)
- [2. Autenticação e Configuração](#2-autenticação-e-configuração)
  - [2.1 Obtenção de Configuração Azure AD (GET /auth/config)](#21-obtenção-de-configuração-azure-ad-get-authconfig)
  - [2.2 Login e Obtenção de Projetos (POST /auth/login)](#22-login-e-obtenção-de-projetos-post-authlogin)
- [3. Gerenciamento de Projetos](#3-gerenciamento-de-projetos)
  - [3.1 Verificar Existência de Projeto (GET /projects/check)](#31-verificar-existência-de-projeto-get-projectscheck)
  - [3.2 Listar Projetos do Usuário (GET /projects/list)](#32-listar-projetos-do-usuário-get-projectslist)
- [4. Início de Análise](#4-início-de-análise)
  - [4.1 Iniciar Análise (POST /analysis/start)](#41-iniciar-análise-post-analysisstart)
- [5. Gerenciamento de Sessão e Relatórios](#5-gerenciamento-de-sessão-e-relatórios)
  - [5.1 Consultar Relatórios do Projeto (GET /session/project/{project_id}/reports)](#51-consultar-relatórios-do-projeto-get-sessionprojectproject_idreports)
  - [5.2 Atualizar Relatório Individual (PUT /session/project/{project_id}/report)](#52-atualizar-relatório-individual-put-sessionprojectproject_idreport)
  - [5.3 Salvar Estado do Projeto (POST /session/project/{project_id}/save-state)](#53-salvar-estado-do-projeto-post-sessionprojectproject_idsave-state)
  - [5.4 Listar Arquivos DOCX do Projeto (GET /session/project/{project_id}/docx-files)](#54-listar-arquivos-docx-do-projeto-get-sessionprojectproject_iddocx-files)
  - [5.5 Consultar Estado Individual de Report (GET /session/project/{project_id}/report/{report_type})](#55-consultar-estado-individual-de-report-get-sessionprojectproject_idreportreport_type)
- [6. Webhooks MCP → Backend](#6-webhooks-mcp--backend)
  - [6.1 Webhook de Progresso/Conclusão/Erro (POST /webhooksmcp)](#61-webhook-de-progresso-conclusão-erro-post-webhooksmcp)
- [7. Tratamento de Erros](#7-tratamento-de-erros)
- [8. Fluxo Completo de Comunicação Frontend ↔ Backend ↔ MCP](#8-fluxo-completo-de-comunicação-frontend-↔-backend-↔-mcp)
- [9. Boas Práticas de Integração](#9-boas-práticas-de-integração)

---

# 2.2 Login e Obtenção de Projetos (POST /auth/login)

Fluxo:
1. O frontend envia o token JWT via header Authorization.
2. O backend valida o token usando AzureADService, extrai o usuario_executor dos claims.
3. O backend busca os projetos associados ao usuario_executor usando ProjectStateService._fetch_and_sanitize_projects.
4. O backend retorna para o frontend a lista de projetos de resumo (campos: nome_projeto, ultima_analysis_type, created_at, ultima_atualizacao, project_id).

Exemplo de requisição:
POST /auth/login HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

Exemplo de resposta de sucesso:
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
      "ultima_analysis_type": "criacao_epicos_azure_devops",
      "created_at": "2024-06-01T12:00:00Z",
      "ultima_atualizacao": "2024-06-01T12:30:00Z",
      "project_id": "projeto-uuid-123"
    }
  ]
}

Exemplo de resposta de erro (token expirado):
{
  "detail": "Token Azure AD expirado."
}

Exemplo de resposta de erro (token inválido):
{
  "detail": "Token Azure AD inválido: ..."
}
