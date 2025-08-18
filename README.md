# MCP Server - Multi-Agent Code Platform

## Visão Geral

MCP Server é uma plataforma robusta para orquestração de agentes de IA que analisam, refatoram e melhoram código-fonte automaticamente. A plataforma utiliza modelos de linguagem avançados (LLMs) como GPT-4 e Claude, integra-se com GitHub para leitura e escrita de código, e oferece uma API RESTful para interação.

## Arquitetura

O sistema é composto por:

- **API FastAPI**: Interface principal para iniciar análises e consultar resultados
- **Agentes de IA**: Componentes especializados que utilizam LLMs para diferentes tarefas
- **Redis**: Armazenamento de estado dos jobs e resultados intermediários
- **Azure Key Vault**: Gerenciamento seguro de credenciais e segredos
- **GitHub Integration**: Leitura de repositórios e criação automática de Pull Requests

## Pré-requisitos

- Python 3.9+
- Redis
- Conta Azure com Key Vault configurado
- Acesso à API da OpenAI e/ou Anthropic (Claude)
- Acesso à API do GitHub
- Azure AI Search (para funcionalidade RAG)

## Instalação

bash
# Clone o repositório
git clone https://github.com/LucioFlavioRosa/agent.git
cd agent

# Instale as dependências
pip install -r requirements.txt


## Configuração do Ambiente

1. Copie o arquivo `.env.example` para `.env` e preencha as variáveis necessárias:

bash
cp .env.example .env
# Edite o arquivo .env com seus valores


2. Configure o Azure Key Vault com os seguintes segredos:
   - `openaiapi`: Chave da API da OpenAI
   - `ANTHROPICAPIKEY`: Chave da API da Anthropic (Claude)
   - `aisearchapi`: Chave da API do Azure AI Search
   - `githubapi`: Token de acesso pessoal do GitHub com permissões para leitura e escrita em repositórios

3. Copie o arquivo `workflows.yaml.example` para `workflows.yaml`:

bash
cp workflows.yaml.example workflows.yaml
# Personalize o arquivo workflows.yaml conforme necessário


## Execução

bash
# Inicie o servidor FastAPI com hot-reload para desenvolvimento
uvicorn mcp_server_fastapi:app --reload

# Para produção
uvicorn mcp_server_fastapi:app --host 0.0.0.0 --port 8000


O servidor estará disponível em `http://localhost:8000`. A documentação da API pode ser acessada em `http://localhost:8000/docs`.

## Uso da API

### Iniciar uma Análise

bash
curl -X POST "http://localhost:8000/start-analysis" \
     -H "Content-Type: application/json" \
     -d '{
           "repo_name": "usuario/repositorio",
           "analysis_type": "refatoracao_codigo",
           "branch_name": "main",
           "instrucoes_extras": "Foque em melhorar a legibilidade",
           "usar_rag": true,
           "gerar_relatorio_apenas": false
         }'


### Verificar Status de um Job

bash
curl -X GET "http://localhost:8000/status/{job_id}"


### Aprovar ou Rejeitar um Job

bash
curl -X POST "http://localhost:8000/update-job-status" \
     -H "Content-Type: application/json" \
     -d '{
           "job_id": "seu-job-id",
           "action": "approve",
           "observacoes": "Parece bom, pode prosseguir"
         }'


### Obter Relatório de Análise

bash
curl -X GET "http://localhost:8000/jobs/{job_id}/report"


## Testes

bash
# Execute os testes unitários
python -m pytest tests/

# Execute os testes com cobertura
python -m pytest --cov=. tests/


## Contribuição

Veja o arquivo [CONTRIBUTING.md](CONTRIBUTING.md) para instruções detalhadas sobre como contribuir com o projeto.

## Changelog

Veja o arquivo [CHANGELOG.md](CHANGELOG.md) para um histórico de mudanças do projeto.
