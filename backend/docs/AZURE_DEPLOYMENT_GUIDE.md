# Guia de Deploy do Backend Peers CodeAI no Azure App Service

## 1. Pré-requisitos de Infraestrutura Azure
- Azure App Service (Web App for Linux)
- Azure Key Vault(s) (ex: kv-codeai-azure-dev-usc, kv-codeai-devops-dev-usc, etc.)
- Azure Blob Storage Account (ex: codeai-storage)
- Azure Cache for Redis
- Azure AD (para autenticação)

## 2. Configuração de Variáveis de Ambiente no App Service
No portal do Azure, acesse seu App Service > Configurações > Configurações de Aplicativo. Adicione as variáveis conforme `backend/docs/ENVIRONMENT_VARIABLES.md`.

## 3. Mapeamento de Key Vaults Múltiplos
- Defina as URLs dos Key Vaults nas variáveis:
  - `AZURE_KV_URL=https://kv-codeai-azure-dev-usc.vault.azure.net/`
  - `DEVOPS_KV_URL=https://kv-codeai-devops-dev-usc.vault.azure.net/`
  - `GITHUB_KV_URL=https://kv-codeai-github-dev-usc.vault.azure.net/`
  - `LLM_KV_URL=https://kv-codeai-llm-dev-usc.vault.azure.net/`
- O backend irá consultar cada Key Vault conforme o tipo de segredo (veja `KEY_VAULT_SECRETS_MAPPING.md`).

## 4. Como Salvar a String de Conexão do Blob Storage no Key Vault
- No Azure Portal ou CLI, crie o segredo no Key Vault principal:
  - Nome do segredo: `azure-storage-connection-string` (use hífens)
  - Valor: string de conexão do Blob Storage (obtida no portal do Storage Account)
- O backend buscará este valor automaticamente via Managed Identity.
- **Importante:** O segredo `AZURE_STORAGE_CONNECTION_STRING` deve estar no Key Vault `kv-codeai-azure-dev-usc` com o nome `azure-storage-connection-string`. Não defina como variável de ambiente no App Service.
- Exemplo de comando Azure CLI:

sh
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name azure-storage-connection-string --value "<sua-string-de-conexao>"


## 5. Configuração da Conexão com o Cache Redis
- Os segredos do Redis **NÃO** devem ser definidos como variáveis de ambiente no App Service.
- No portal do Azure, acesse seu Redis Cache e copie:
  - Host: `REDIS_HOST` (crie como segredo `redis-host` no Key Vault)
  - Porta: `REDIS_PORT` (crie como segredo `redis-port` no Key Vault, use 6380 para SSL)
  - Senha: `REDIS_PASSWORD` (crie como segredo `redis-password` no Key Vault)
  - Database: `REDIS_DB` (crie como segredo `redis-db` no Key Vault, normalmente 0)
  - `REDIS_USE_SSL` (crie como segredo `redis-use-ssl` no Key Vault, valor `True`)
  - `REDIS_SSL_CERT_REQS` (crie como segredo `redis-ssl-cert-reqs` no Key Vault, valor `required`)
- Estes segredos devem ser criados no Key Vault `kv-codeai-azure-dev-usc` usando nomes com hífens.
- O backend irá carregar automaticamente esses valores do Key Vault via Managed Identity.
- Para ambientes com Redis em subrede privada, utilize o endpoint privado do Redis. O App Service deve estar integrado à mesma VNET/subrede do Redis (VNET Integration).

## 6. Managed Identity Setup
- No App Service, habilite "Identidade Gerenciada" (System-assigned).
- Dê permissão de "Get" e "List" nos Key Vaults para esta identidade.
- Dê permissão de "Storage Blob Data Contributor" no Storage Account.

## 7. Passo a Passo para Deploy
1. Crie todos os recursos Azure necessários.
2. Configure as variáveis de ambiente no App Service.
3. Crie os segredos nos Key Vaults (veja `KEY_VAULT_SECRETS_MAPPING.md`).
4. Habilite Managed Identity e configure permissões.
5. Configure o App Service para VNET Integration com a mesma subrede do Redis.
6. Faça deploy do código (zip, GitHub Actions, ou Azure CLI).
7. Reinicie o App Service.
8. Teste conectividade usando o endpoint `/health/infrastructure`.

## 8. Testando o Backend
- Use os exemplos de payload em `API_PAYLOAD_EXAMPLES.md` para testar os endpoints.
- Para autenticação, obtenha um token Azure AD (MSAL.js, Postman, ou Azure Portal).
