# Multi-Agent Code Platform (MCP)

Servidor robusto para orquestração de agentes de IA em workflows de modernização, revisão e aplicação incremental de código.

## Pré-requisitos

- Python 3.8+
- Redis (para orquestração e cache)
- Azure Storage Account (para armazenamento de relatórios e checkpoints)
- GitHub/GitLab/Azure DevOps account (para integração com repositórios)
- (Opcional) Chaves de API para LLMs (OpenAI, Claude, etc.)

## Instalação

1. Clone o repositório:
   bash
   git clone https://github.com/seu-usuario/seu-repositorio.git
   cd seu-repositorio
   
2. Crie um ambiente virtual (opcional, mas recomendado):
   bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate    # Windows
   
3. Instale as dependências:
   bash
   pip install -r requirements.txt
   

## Configuração

1. Copie o arquivo de exemplo de variáveis de ambiente:
   bash
   cp .env.example .env
   
2. Edite o arquivo `.env` com os valores apropriados para seu ambiente:
   - `AZURE_STORAGE_ACCOUNT_URL`
   - `AZURE_STORAGE_CONTAINER_NAME`
   - `REDIS_HOST`
   - `REDIS_PORT`
   - Chaves de API e tokens de acesso conforme necessário

## Como Executar

Inicie o servidor FastAPI com:
bash
uvicorn mcp_server_fastapi:app --reload


A documentação interativa da API estará disponível em [http://localhost:8000/docs](http://localhost:8000/docs).

## Como Rodar os Testes

Execute a suíte de testes com:
bash
pytest -v

ou
bash
python -m pytest


## Arquitetura

O MCP é baseado em uma arquitetura de agentes, workflows e serviços:

- **Agentes:** Responsáveis por tarefas especializadas (processamento, revisão, aplicação incremental, comparação, etc.)
- **Workflows:** Orquestram a sequência de agentes para cada tipo de análise ou modernização
- **Serviços:** Camadas de abstração para integração com repositórios, armazenamento, LLMs, cache, etc.

Para detalhes técnicos, consulte a documentação em [`docs/`](./docs/):
- [`docs/workflow.md`](./docs/workflow.md): Visão geral dos workflows
- [`docs/incremental_changes_system.md`](./docs/incremental_changes_system.md): Sistema de aplicação incremental de mudanças
- [`docs/banco_rbac.md`](./docs/banco_rbac.md): Modelo de RBAC

## Endpoints da API

Principais endpoints disponíveis:

- `POST /start-analysis` — Inicia uma nova análise de código
- `POST /update-job-status` — Aprova ou rejeita um job em andamento
- `GET /jobs/{job_id}/report` — Obtém o relatório de análise de um job
- `GET /analyses/by-name/{analysis_name}` — Busca análise por nome
- `POST /start-code-generation-from-report/{analysis_name}` — Gera código a partir de um relatório existente
- `GET /status/{job_id}` — Consulta o status de um job
- `GET /reports/{report_name}/jobs` — Lista jobs associados a um relatório
- `POST /resume-incremental-changes/{job_id}` — Retoma aplicação incremental de mudanças

Consulte a [documentação interativa do FastAPI](http://localhost:8000/docs) para detalhes completos de parâmetros, payloads e respostas.

## Contribuindo

Contribuições são bem-vindas! Veja o arquivo [`CONTRIBUTING.md`](./CONTRIBUTING.md) para detalhes sobre o fluxo de trabalho, padrões de código e como configurar o ambiente de desenvolvimento.

## Histórico de mudanças

Consulte o [`CHANGELOG.md`](./CHANGELOG.md) para acompanhar as principais alterações e versões do projeto.

---

> **Dica:** Revise periodicamente os templates de Issue e Pull Request em `.github/` para garantir alinhamento com o fluxo de trabalho atual.
