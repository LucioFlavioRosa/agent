# Multi-Agent Code Platform (MCP)

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/seu-usuario/seu-repo/actions)
[![Coverage Status](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/seu-usuario/seu-repo)
[![Version](https://img.shields.io/badge/version-9.0.0-blue)](https://github.com/seu-usuario/seu-repo/releases)

Servidor robusto para orquestração de agentes de IA, análise e modernização de código, baseado em FastAPI, Redis e arquitetura multi-agente.

## Sumário
- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Configuração de Ambiente](#configuração-de-ambiente)
- [Como Executar os Testes](#como-executar-os-testes)
- [Exemplos de Uso da API](#exemplos-de-uso-da-api)
- [Contribuindo](#contribuindo)
- [Changelog](#changelog)

## Visão Geral
O MCP (Multi-Agent Code Platform) é uma plataforma extensível para automação de fluxos de trabalho de análise e refatoração de código, utilizando agentes inteligentes e integração com múltiplos provedores de repositório (GitHub, GitLab, Azure DevOps).

## Arquitetura do Sistema


+-------------------+
|    FastAPI        |
+-------------------+
          |
          v
+-------------------+
|   Workflow        |
|   Orchestrator    |
+-------------------+
          |
          v
+-------------------+
|    Redis          |
+-------------------+
          |
          v
+-------------------+
|  Agentes (Python) |
|  - Aplicador      |
|  - Revisor        |
|  - Comparador     |
|  - Processador    |
+-------------------+
          |
          v
+-------------------+
| Repositórios      |
| (GitHub/GitLab/   |
|  Azure DevOps)    |
+-------------------+


- **FastAPI**: expõe endpoints REST para orquestração e monitoramento.
- **Workflow Orchestrator**: gerencia a execução dos agentes e etapas do fluxo.
- **Redis**: fila de tarefas, cache e checkpoint de execuções.
- **Agentes**: executam tarefas especializadas (aplicação de mudanças, revisão, comparação, processamento).
- **Repositórios**: integração com múltiplos provedores.

## Configuração de Ambiente

1. **Clone o repositório:**
   bash
   git clone https://github.com/seu-usuario/seu-repo.git
   cd seu-repo
   

2. **Crie e configure o arquivo de variáveis de ambiente:**
   - Renomeie `.env.example` para `.env` e preencha com suas credenciais e configurações.
   - Consulte o arquivo `.env.example` para detalhes sobre cada variável.

3. **Instale as dependências:**
   bash
   pip install -r requirements.txt
   

4. **Inicie o Redis:**
   - Certifique-se de que o Redis está rodando localmente ou configure o acesso conforme sua infraestrutura.

5. **Execute o servidor FastAPI:**
   bash
   uvicorn mcp_server_fastapi:app --reload
   

## Como Executar os Testes

Execute todos os testes automatizados com:

bash
pytest -v tests/


## Exemplos de Uso da API

### Iniciar uma análise

bash
curl -X POST "http://localhost:8000/start-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name_modernizado": "seu-org/seu-repo",
    "branch_name_modernizado": "main",
    "projeto": "projeto-exemplo",
    "analysis_type": "modernizacao",
    "repository_type": "github"
  }'


### Buscar relatório de um job

bash
curl -X GET "http://localhost:8000/jobs/{job_id}/report"


### Exemplo em Python (requests)

python
import requests

payload = {
    "repo_name_modernizado": "seu-org/seu-repo",
    "branch_name_modernizado": "main",
    "projeto": "projeto-exemplo",
    "analysis_type": "modernizacao",
    "repository_type": "github"
}
resp = requests.post("http://localhost:8000/start-analysis", json=payload)
print(resp.json())


## Contribuindo

Veja o arquivo [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes detalhadas sobre configuração de ambiente, fluxo de trabalho para Pull Requests, padrões de código e execução de testes.

## Changelog

Consulte o arquivo [CHANGELOG.md](CHANGELOG.md) para o histórico de versões e mudanças.
