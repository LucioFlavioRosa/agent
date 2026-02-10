# Mapeamento de Segredos: Key Vault → Settings

| Nome no Key Vault         | Atributo no Settings   | Key Vault de Origem         | Descrição                                               |
|--------------------------|------------------------|-----------------------------|---------------------------------------------------------|
| redis-host                | REDIS_HOST             | kv-codeai-azure-dev-usc     | Host do Azure Redis Cache                               |
| redis-port                | REDIS_PORT             | kv-codeai-azure-dev-usc     | Porta do Redis (6380 para SSL)                          |
| redis-password            | REDIS_PASSWORD         | kv-codeai-azure-dev-usc     | Senha do Redis                                          |
| redis-db                  | REDIS_DB               | kv-codeai-azure-dev-usc     | Database Redis                                          |
| redis-use-ssl             | REDIS_USE_SSL          | kv-codeai-azure-dev-usc     | Habilita conexão SSL/TLS com Redis                      |
| redis-ssl-cert-reqs       | REDIS_SSL_CERT_REQS    | kv-codeai-azure-dev-usc     | Requisição de certificado SSL ('required' recomendado)   |

## Como criar segredos no Key Vault

### Usando Azure CLI:

az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-host --value "<host>"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-port --value "6380"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-password --value "<senha>"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-db --value "0"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-use-ssl --value "True"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-ssl-cert-reqs --value "required"

> Apenas segredos do Redis são necessários no Key Vault para o backend. Segredos de Azure AD e Blob Storage não são mais utilizados nem mapeados pelo backend.
