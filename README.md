# Multi-Agent Code Platform (MCP Server)

## Dependências

Certifique-se de instalar todas as dependências listadas em `requirements.txt`:


pip install -r requirements.txt


Principais pacotes:
- azure-identity
- azure-keyvault-secrets
- azure-search-documents
- openai
- anthropic
- redis
- PyGithub
- pydantic
- fastapi
- pyyaml

## Variáveis de Ambiente

Crie um arquivo `.env` baseado em `.env.example` com os seguintes campos:


KEY_VAULT_URL=https://<seu-key-vault>.vault.azure.net/
AZURE_OPENAI_MODELS=https://<seu-endpoint-openai>.openai.azure.com/
AZURE_OPENAI_EMBEDDING_MODEL_NAME=text-embedding-ada-002
AZURE_DEFAULT_DEPLOYMENT_NAME=gpt-4o
AI_SEARCH_ENDPOINT=https://<seu-endpoint-search>.search.windows.net/
AI_SEARCH_INDEX_NAME=policy-index
REDIS_URL=redis://:<senha>@<host>:<porta>/0


## Segredos no Azure Key Vault

Certifique-se de criar os seguintes segredos no seu Key Vault:
- `azure-openai-modelos`: Chave de API do Azure OpenAI
- `openaiapi`: Chave de API do OpenAI
- `aisearchapi`: Chave de API do Azure Search
- `ANTHROPICAPIKEY`: Chave de API da Anthropic
- `github-token-<org>`: Token de acesso do GitHub por organização

## Observações
- O sistema depende de indexação correta do analysis_name para busca de relatórios por nome.
- O endpoint `/jobs/by-name/{analysis_name}/report` retorna erro 404 se o nome não for indexado.
- O parâmetro `max_token_out` deve ser ajustado conforme o limite do provedor LLM.
- Os testes devem ser executados com Redis disponível e configurado.
