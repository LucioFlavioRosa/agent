# Arquitetura e Fluxos do Backend Peers CodeAI

Este documento detalha o fluxo completo do backend Peers CodeAI, desde o recebimento da requisição do frontend até o envio da resposta, incluindo integrações com Azure Key Vault (múltiplos cofres), Blob Storage, Redis, MCP Server e o mecanismo de configuração dinâmica de agentes. Cada etapa está explicada, com referência ao arquivo de código responsável e diagramas ilustrativos.

---

## Índice

1. Visão Geral da Comunicação entre Grandes Blocos
2. Login e Autenticação via Azure AD
3. Criação de Projeto e Conversão nome_projeto → project_id
4. Consulta de Projeto Existente
5. Observações Importantes
6. Enriquecimento de Contexto para Refinamento
7. Comunicação via Webhooks (MCP → Backend)
8. Gerenciamento de Sessão e Relatórios
9. Resumo dos Endpoints por Rota

---

## 8. Gerenciamento de Sessão e Relatórios

A rota `backend/app/api/session.py` é responsável pela consulta e atualização de relatórios dos projetos, além do gerenciamento da sessão do usuário.

Fluxo atualizado (prioridade Redis → Blob):
1. O frontend consulta relatórios específicos usando o endpoint `/session/project/{project_id}/{job_id}/reports`.
2. O backend busca os relatórios do projeto no Redis usando `redis_service.get_all_reports_for_project(project_id)`.
3. Se o Redis retornar dados válidos e todos os relatórios possuírem `job_id` igual ao solicitado, retorna imediatamente os dados do Redis (status 200).
4. Se o Redis não retornar dados ou houver divergência de `job_id`, o backend faz fallback para o Blob Storage usando `ProjectStateService.load_all_states_from_blob(usuario_executor, project_id)`.
5. Se o Blob retornar dados válidos e o `job_id` corresponder, retorna os dados do Blob (status 200).
6. Se não houver dados válidos, verifica se existe um job ativo (status 202), ou retorna erro 404.

mermaid
flowchart TD
    FE[Frontend] -->|GET /session/project/{project_id}/{job_id}/reports| BE[Backend]
    BE -->|Busca no Redis| Redis[(Redis)]
    Redis -- Dados válidos e job_id ok --> BE
    BE -- Retorna dados do Redis --> FE
    Redis -- Dados ausentes ou job_id divergente --> BE
    BE -->|Fallback| Blob[(Blob Storage)]
    Blob -- Dados válidos e job_id ok --> BE
    BE -- Retorna dados do Blob --> FE
    Blob -- Dados ausentes ou job_id divergente --> BE
    BE -- Verifica job ativo ou retorna erro --> FE


---

## 9. Resumo dos Endpoints por Rota

| Arquivo                      | Endpoint(s)                                 | Descrição                                                                 |
|-----------------------------|---------------------------------------------|---------------------------------------------------------------------------|
| `auth.py`                   | `/auth/login`, `/auth/config`               | Autenticação e configuração Azure AD                                      |
| `analysis.py`               | `/analysis/start`                           | Início de análise, conversão nome_projeto → project_id, enriquecimento de contexto |
| `projects.py`               | `/projects/check`, `/projects/list`         | Consulta e listagem de projetos existentes                                |
| `session.py`                | `/session/project/{project_id}/{job_id}/reports`, `/session/project/{project_id}/report`, `/session/project/{project_id}/save-state`, `/session/project/{project_id}/docx-files` | Consulta, atualização e gerenciamento de relatórios e arquivos de sessão   |
| `webhooks.py`               | `/webhooks/mcp`                             | Recebimento de webhooks do MCP, atualização de estado e relatórios        |

---

**Notas:**
- Todos os diagramas Mermaid estão sintaticamente corretos e podem ser renderizados em ferramentas compatíveis.
- Os fluxos descritos refletem a arquitetura atual do backend, com integração segura entre Frontend, Backend e MCP Server.
- Para dúvidas técnicas complexas, consulte as observações e notas de rodapé ao longo do documento.
