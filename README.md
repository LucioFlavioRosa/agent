# MCP Server - Multi-Agent Code Platform

## Visão Geral

O MCP Server é uma plataforma robusta para orquestração de agentes de IA que analisam e refatoram código-fonte. A plataforma utiliza uma arquitetura baseada em FastAPI, Redis para armazenamento de jobs, e integração com GitHub, Azure Key Vault e Azure AI Search.

## Arquitetura

- **FastAPI**: Framework web para exposição de endpoints RESTful
- **Redis**: Armazenamento de estado dos jobs
- **GitHub API**: Leitura e escrita de repositórios
- **Azure Key Vault**: Gerenciamento seguro de segredos
- **Azure AI Search**: Suporte a RAG (Retrieval-Augmented Generation)
- **Agentes de IA**: Componentes modulares para análise e processamento de código

## Pré-requisitos

- Python 3.10 ou superior
- Acesso a um Azure Key Vault
- Instância Redis
- Conta GitHub com token de acesso
- Acesso à API da OpenAI e/ou Anthropic (opcional)
- Azure AI Search configurado (opcional, para RAG)

## Instalação

bash
# Clone o repositório
git clone https://github.com/seu-usuario/mcp-server.git
cd mcp-server

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente (copie de .env.example)
cp .env.example .env
# Edite o arquivo .env com suas configurações


## Configuração de Ambiente

Crie um arquivo `.env` baseado no `.env.example` fornecido. As principais variáveis necessárias são:

- `KEY_VAULT_URL`: URL do seu Azure Key Vault
- `REDIS_URL`: URL de conexão com o Redis
- `AI_SEARCH_ENDPOINT`: Endpoint do Azure AI Search (para RAG)
- `AI_SEARCH_INDEX_NAME`: Nome do índice no Azure AI Search
- `AZURE_OPENAI_EMBEDDING_MODEL_NAME`: Nome do modelo de embeddings

No Azure Key Vault, você precisa configurar os seguintes segredos:

- `githubapi`: Token de acesso ao GitHub
- `openaiapi`: Chave da API da OpenAI
- `aisearchapi`: Chave da API do Azure AI Search
- `ANTHROPICAPIKEY`: Chave da API da Anthropic (opcional)

## Execução Local

bash
# Autentique-se no Azure (para DefaultAzureCredential funcionar localmente)
az login

# Inicie o servidor
uvicorn mcp_server_fastapi:app --host 0.0.0.0 --port 8000


Acesse a documentação da API em: http://localhost:8000/docs

## Testes

bash
# Execute os testes
pytest -q


## Guia Rápido da API

### Iniciar uma Análise

bash
POST /start-analysis


Payload de exemplo:

{
  "repo_name": "usuario/repositorio",
  "analysis_type": "auditoria_documentacao",
  "branch_name": "main",
  "instrucoes_extras": "Foque em problemas de segurança",
  "usar_rag": true,
  "gerar_relatorio_apenas": false,
  "model_name": "gpt-4o"
}


### Atualizar Status do Job

bash
POST /update-job-status


Payload de exemplo:

{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "action": "approve",
  "observacoes": "Aprovado para implementação"
}


### Obter Relatório

bash
GET /jobs/{job_id}/report


### Verificar Status

bash
GET /status/{job_id}


## Deploy no Azure App Service

### Configuração do App Service

1. **Habilitar Managed Identity**:
   - No portal Azure, acesse seu App Service
   - Vá para "Identity" e habilite "System assigned"

2. **Conceder Acesso ao Key Vault**:
   - No Key Vault, vá para "Access policies" ou "Access control (IAM)"
   - Adicione a Managed Identity do App Service com a role "Key Vault Secrets User"

3. **Configurar App Settings**:
   - `KEY_VAULT_URL`: URL do seu Azure Key Vault
   - `REDIS_URL`: URL de conexão com o Redis
   - `AI_SEARCH_ENDPOINT`: Endpoint do Azure AI Search
   - `AI_SEARCH_INDEX_NAME`: Nome do índice no Azure AI Search
   - `AZURE_OPENAI_EMBEDDING_MODEL_NAME`: Nome do modelo de embeddings

4. **Configurar Segredos no Key Vault**:
   - `githubapi`: Token de acesso ao GitHub
   - `openaiapi`: Chave da API da OpenAI
   - `aisearchapi`: Chave da API do Azure AI Search
   - `ANTHROPICAPIKEY`: Chave da API da Anthropic (opcional)

### Implantação

bash
# Deploy via Azure CLI
az webapp up --name seu-app-service --resource-group seu-grupo-recursos


## Arquivo workflows.yaml

O servidor depende do arquivo `workflows.yaml` na raiz do projeto, que define os tipos de análise disponíveis e suas configurações. Certifique-se de que este arquivo exista e contenha pelo menos uma configuração válida antes de iniciar o servidor.

O parâmetro `analysis_type` no endpoint `/start-analysis` deve corresponder a uma das chaves definidas neste arquivo.