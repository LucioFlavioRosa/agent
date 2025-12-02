# Variáveis de Ambiente do Backend Peers CodeAI

| Nome da Variável                | Descrição                                               | Obrigatória | Valor Padrão | Exemplo                                                      |
|---------------------------------|---------------------------------------------------------|-------------|--------------|--------------------------------------------------------------|
| AZURE_KV_URL                    | URL do Key Vault principal (Azure)                      | Sim         | -            | https://kv-codeai-azure-dev-usc.vault.azure.net/             |
| DEVOPS_KV_URL                   | URL do Key Vault DevOps                                 | Não         | -            | https://kv-codeai-devops-dev-usc.vault.azure.net/            |
| GITHUB_KV_URL                   | URL do Key Vault GitHub                                 | Não         | -            | https://kv-codeai-github-dev-usc.vault.azure.net/            |
| LLM_KV_URL                      | URL do Key Vault LLM                                    | Não         | -            | https://kv-codeai-llm-dev-usc.vault.azure.net/               |
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

> **Observação Importante:** As variáveis do Redis (`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB`, `REDIS_USE_SSL`, `REDIS_SSL_CERT_REQS`) **NÃO** devem ser definidas como variáveis de ambiente no App Service. Elas devem ser criadas como segredos no Key Vault `kv-codeai-azure-dev-usc` usando nomes com hífens (exemplo: `redis-host`). O backend irá carregar automaticamente esses valores do Key Vault via Managed Identity.

> **Observação:** Segredos sensíveis devem ser criados no Key Vault usando nomes com hífens. O backend faz o mapeamento automaticamente.
> **Observação:** Para ambientes com Azure Cache for Redis em subrede privada, é obrigatório configurar os segredos do Redis no Key Vault e garantir que o App Service esteja integrado à mesma VNET/subrede do Redis.
