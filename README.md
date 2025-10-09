# Multi-Agent Code Platform (MCP Server)

Servidor robusto para orquestração de agentes de IA em fluxos de modernização, revisão e aplicação incremental de código, utilizando FastAPI, Redis e integração com múltiplos provedores de repositório (GitHub, GitLab, Azure DevOps).

## Índice
- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Configuração de Ambiente](#configuração-de-ambiente)
- [Como Executar os Testes](#como-executar-os-testes)
- [Exemplos de Uso da API](#exemplos-de-uso-da-api)
- [Documentação e Contribuição](#documentação-e-contribuição)

## Visão Geral

O MCP Server centraliza a execução de workflows inteligentes para análise, refatoração e modernização de código, suportando execução incremental, geração de relatórios e integração com LLMs (OpenAI, Claude, etc.).

## Arquitetura do Sistema

O sistema é composto pelos seguintes módulos principais:

- **FastAPI**: API principal para orquestração e gerenciamento de jobs.
- **Redis**: Utilizado para cache, filas e checkpoints de execução incremental.
- **Agentes**: Scripts especializados para análise, revisão e aplicação de mudanças em código.
- **Workflows**: Definidos em YAML e Python, coordenam a sequência de agentes e etapas.
- **Serviços de Integração**: Comunicação com provedores de repositório (GitHub, GitLab, Azure DevOps), armazenamento de blobs e provedores de LLM.


+-------------------+
|    Usuário/API    |
+--------+----------+
         |
         v
+-------------------+
|     FastAPI       |
+--------+----------+
         |
         v
+-------------------+
|   Workflow Orq.   |
+--------+----------+
         |
   +-----+-----+-------------------+
   |           |                   |
   v           v                   v
[Agentes]   [Redis]     [Repositórios/LLM/Blob]


## Configuração de Ambiente

1. **Clone o repositório:**

   bash
   git clone <URL_DO_REPOSITORIO>
   cd <PASTA_DO_REPOSITORIO>
   

2. **Crie e configure o arquivo de variáveis de ambiente:**

   Copie o arquivo de exemplo e edite conforme necessário:

   bash
   cp .env.example .env
   # Edite .env com suas credenciais e configurações
   

   Consulte o arquivo `.env.example` para a lista completa de variáveis obrigatórias (Azure, Redis, GitHub/GitLab/Azure DevOps, LLMs, etc).

3. **Instale as dependências:**

   bash
   pip install -r requirements.txt
   

4. **Inicialize serviços auxiliares:**

   - Certifique-se de que o Redis está rodando (padrão: localhost:6379).
   - Configure o acesso aos serviços de blob e repositórios conforme necessário.

## Como Executar os Testes

Execute todos os testes automatizados utilizando o Pytest:

bash
pytest -v tests/


## Exemplos de Uso da API

### Iniciar uma Análise

bash
curl -X POST http://localhost:8000/start-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name_modernizado": "org/repo",
    "branch_name_modernizado": "main",
    "projeto": "MeuProjeto",
    "analysis_type": "modernizacao",
    "repository_type": "github"
  }'


### Exemplo em Python (requests)

python
import requests

payload = {
    "repo_name_modernizado": "org/repo",
    "branch_name_modernizado": "main",
    "projeto": "MeuProjeto",
    "analysis_type": "modernizacao",
    "repository_type": "github"
}
resp = requests.post("http://localhost:8000/start-analysis", json=payload)
print(resp.json())


## Documentação e Contribuição

- Consulte a pasta [`docs/`](docs/) para documentação técnica detalhada (workflow, RBAC, sistema incremental).
- Veja o arquivo [`CONTRIBUTING.md`](CONTRIBUTING.md) para orientações sobre configuração do ambiente, padrões de código e fluxo de Pull Requests.
- Consulte o [`CHANGELOG.md`](CHANGELOG.md) para histórico de versões e mudanças.

---

> **Dica:** Considere adicionar badges de status de build, cobertura de testes e versão para aumentar a transparência do projeto.
