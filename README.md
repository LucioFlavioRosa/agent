# Multi-Agent Code Platform (MCP)

## Variáveis de Ambiente Obrigatórias

Crie um arquivo `.env` com as seguintes chaves:


KEY_VAULT_URL=https://<nome-do-key-vault>.vault.azure.net/
AZURE_OPENAI_MODELS=https://<endpoint-do-azure-openai>.openai.azure.com/
AZURE_OPENAI_EMBEDDING_MODEL_NAME=text-embedding-ada-002
AZURE_DEFAULT_DEPLOYMENT_NAME=gpt-4-turbo
AI_SEARCH_ENDPOINT=https://<endpoint-do-azure-search>.search.windows.net
AI_SEARCH_INDEX_NAME=policy-index
REDIS_URL=redis://:<senha>@<host>:<porta>/0


## Instalação de Dependências


pip install -r requirements.txt


## Endpoints Principais

### Criar Análise


POST /start-analysis
{
  "repo_name": "org/testrepo",
  "analysis_type": "default",
  "branch_name": "main",
  "instrucoes_extras": "Texto livre",
  "usar_rag": false,
  "gerar_relatorio_apenas": true,
  "model_name": null,
  "analysis_name": "nome-unico-da-analise"
}


### Buscar relatório por nome de análise


GET /analyses/by-name/{analysis_name}


### Iniciar geração de código a partir de relatório existente


POST /start-code-generation-from-report/{analysis_name}


## Dependências Obrigatórias

- anthropic
- openai
- azure-identity
- azure-keyvault-secrets
- azure-search-documents
- PyGithub
- pytest
- fastapi
- pydantic
- redis
- yaml

## Observações
- O campo `analysis_type` depende do arquivo `workflows.yaml`.
- O sistema assume sobrescrita para nomes duplicados de análise.
- O job expira conforme TTL do Redis.

## Exemplos de Uso
Consulte os testes em `backend/tests/test_analysis_naming.py` para exemplos completos de fluxo.
