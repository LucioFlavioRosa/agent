# Mapeamento de Segredos: Key Vault → Settings

| Nome no Key Vault                   | Atributo no Settings               | Key Vault de Origem                | Descrição                                               |
|-------------------------------------|------------------------------------|------------------------------------|---------------------------------------------------------|
| azure-storage-connection-string     | AZURE_STORAGE_CONNECTION_STRING    | kv-codeai-azure-dev-usc            | String de conexão do Blob Storage                       |
| azure-storage-container-name        | AZURE_STORAGE_CONTAINER_NAME       | kv-codeai-azure-dev-usc            | Nome do container de arquivos                           |
| azure-ad-client-secret              | AZURE_AD_CLIENT_SECRET             | kv-codeai-azure-dev-usc            | Client Secret do Azure AD                               |
| jwt-secret-key                      | JWT_SECRET_KEY                     | kv-codeai-azure-dev-usc            | Chave secreta JWT                                       |
| redis-host                          | REDIS_HOST                         | kv-codeai-azure-dev-usc            | Host do Azure Redis Cache                               |
| redis-port                          | REDIS_PORT                         | kv-codeai-azure-dev-usc            | Porta do Redis (6380 para SSL)                          |
| redis-password                      | REDIS_PASSWORD                     | kv-codeai-azure-dev-usc            | Senha do Redis                                          |
| redis-db                            | REDIS_DB                           | kv-codeai-azure-dev-usc            | Database Redis                                          |
| redis-use-ssl                       | REDIS_USE_SSL                      | kv-codeai-azure-dev-usc            | Habilita conexão SSL/TLS com Redis                      |
| redis-ssl-cert-reqs                 | REDIS_SSL_CERT_REQS                | kv-codeai-azure-dev-usc            | Requisição de certificado SSL ('required' recomendado)   |
| devops-token                        | DEVOPS_TOKEN                       | kv-codeai-devops-dev-usc           | Token de integração DevOps                              |
| github-token                        | GITHUB_TOKEN                       | kv-codeai-github-dev-usc           | Token de integração GitHub                              |
| llm-api-key                         | LLM_API_KEY                        | kv-codeai-llm-dev-usc              | Chave de API para LLM                                   |

## Como criar segredos no Key Vault

### Usando Azure CLI:
text
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name azure-storage-connection-string --value "<sua-string-de-conexao>"

