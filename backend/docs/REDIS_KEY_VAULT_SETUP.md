# Guia de Configuração dos Segredos do Redis no Key Vault kv-codeai-azure-dev-usc

## 1. Introdução
Este guia explica como configurar os segredos do Azure Cache for Redis no Key Vault principal do projeto (`kv-codeai-azure-dev-usc`). O backend Peers CodeAI carrega esses segredos automaticamente via Managed Identity e **não aceita variáveis de ambiente** para o Redis.

## 2. Lista de Segredos Necessários
Crie os seguintes segredos no Key Vault, usando nomes com hífens:

- `redis-host`              → endpoint privado do Redis (ex: `your-redis-cache.redis.cache.windows.net`)
- `redis-port`              → porta do Redis (ex: `6380` para SSL)
- `redis-password`          → senha do Redis
- `redis-db`                → database do Redis (ex: `0`)
- `redis-use-ssl`           → `True` (habilita SSL/TLS)
- `redis-ssl-cert-reqs`     → `required` (requer certificado SSL)

## 3. Como Criar os Segredos no Azure CLI
```text
sh
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-host --value "your-redis-cache.redis.cache.windows.net"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-port --value "6380"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-password --value "<sua-senha>"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-db --value "0"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-use-ssl --value "True"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name redis-ssl-cert-reqs --value "required"
```

## 4. Validação dos Segredos
Após criar os segredos, valide que eles estão presentes:
```text
sh
az keyvault secret list --vault-name kv-codeai-azure-dev-usc
az keyvault secret show --vault-name kv-codeai-azure-dev-usc --name redis-host
```

## 5. Testando a Conectividade do Backend
Após o deploy, acesse o endpoint `/health/infrastructure` para verificar se o backend está conseguindo conectar ao Redis usando os segredos do Key Vault. Se algum segredo estiver ausente, o backend irá reportar erro crítico na inicialização.

## 6. Observações
- **Nunca** defina as variáveis do Redis como variáveis de ambiente no App Service.
- Sempre use nomes com hífens para os segredos no Key Vault.
- O backend faz o mapeamento automático dos nomes do Key Vault para os atributos do settings.
