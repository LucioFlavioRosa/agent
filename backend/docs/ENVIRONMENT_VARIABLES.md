# Variáveis de Ambiente do Backend Peers CodeAI

| Nome da Variável                | Descrição                                               | Obrigatória | Valor Padrão | Exemplo                                                      |
|---------------------------------|---------------------------------------------------------|-------------|--------------|--------------------------------------------------------------|
| AZURE_KV_URL                    | URL do Key Vault principal (Azure)                      | Sim         | -            | https://kv-codeai-azure-dev-usc.vault.azure.net/             |
| DEVOPS_KV_URL                   | URL do Key Vault DevOps                                 | Não         | -            | https://kv-codeai-devops-dev-usc.vault.azure.net/            |
| GITHUB_KV_URL                   | URL do Key Vault GitHub                                 | Não         | -            | https://kv-codeai-github-dev-usc.vault.azure.net/            |
| LLM_KV_URL                      | URL do Key Vault LLM                                    | Não         | -            | https://kv-codeai-llm-dev-usc.vault.azure.net/               |
| REDIS_HOST                      | Host do Azure Redis Cache                               | Sim         | localhost    | your-redis-cache.redis.cache.windows.net                     |
| REDIS_PORT                      | Porta do Redis (6380 para SSL)                          | Sim         | 6379         | 6380                                                         |
| REDIS_PASSWORD                  | Senha do Redis                                          | Sim         | -            | <obtido-no-portal-azure>                                     |
| REDIS_DB                        | Database Redis                                          | Sim         | 0            | 0                                                            |
| AZURE_STORAGE_CONNECTION_STRING | String de conexão do Blob Storage (via Key Vault)       | Sim         | -            | DefaultEndpointsProtocol=https;AccountName=...               |
| AZURE_STORAGE_CONTAINER_NAME    | Nome do container de arquivos                           | Sim         | arquivos     | arquivos                                                     |
| AZURE_AD_CLIENT_ID              | Client ID do Azure AD                                   | Sim         | -            | <client-id>                                                  |
| AZURE_AD_TENANT_ID              | Tenant ID do Azure AD                                   | Sim         | -            | <tenant-id>                                                  |
| AZURE_AD_CLIENT_SECRET          | Client Secret do Azure AD (via Key Vault)               | Sim         | -            | <client-secret>                                              |
| AZURE_AD_REDIRECT_URI           | URI de redirecionamento do Azure AD                     | Não         | http://localhost:3000/auth/callback | https://your-app.azurewebsites.net/auth/callback |
| JWT_SECRET_KEY                  | Chave secreta JWT (via Key Vault)                       | Sim         | -            | <jwt-secret>                                                 |
| MCP_SERVER_BASE_URL             | URL base do MCP Server                                  | Sim         | -            | https://mcp-app-service.azurewebsites.net                    |
| ALLOWED_IPS                     | Lista de IPs permitidos (separados por vírgula)         | Não         | 127.0.0.1    | 177.104.212.42,200.100.50.25                                 |
| LOG_LEVEL                       | Nível de log (INFO, DEBUG, ERROR)                       | Não         | INFO         | INFO                                                         |

> **Observação:** Segredos sensíveis devem ser criados no Key Vault usando nomes com hífens. O backend faz o mapeamento automaticamente.
