# Mapeamento de Segredos: Key Vault → Settings

| Nome no Key Vault                   | Atributo no Settings               | Key Vault de Origem                | Descrição                                               |
|-------------------------------------|------------------------------------|------------------------------------|---------------------------------------------------------|
| azure-storage-connection-string     | AZURE_STORAGE_CONNECTION_STRING    | kv-codeai-azure-dev-usc            | String de conexão do Blob Storage                       |
| azure-storage-container-name        | AZURE_STORAGE_CONTAINER_NAME       | kv-codeai-azure-dev-usc            | Nome do container de arquivos                           |
| azure-ad-client-secret              | AZURE_AD_CLIENT_SECRET             | kv-codeai-azure-dev-usc            | Client Secret do Azure AD                               |
| jwt-secret-key                      | JWT_SECRET_KEY                     | kv-codeai-azure-dev-usc            | Chave secreta JWT                                       |
| devops-token                        | DEVOPS_TOKEN                       | kv-codeai-devops-dev-usc           | Token de integração DevOps                              |
| github-token                        | GITHUB_TOKEN                       | kv-codeai-github-dev-usc           | Token de integração GitHub                              |
| llm-api-key                         | LLM_API_KEY                        | kv-codeai-llm-dev-usc              | Chave de API para LLM                                   |

## Como criar segredos no Key Vault

### Usando Azure CLI:
```text
bash
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name azure-storage-connection-string --value "<sua-string-de-conexao>"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name azure-ad-client-secret --value "<seu-client-secret>"
az keyvault secret set --vault-name kv-codeai-azure-dev-usc --name jwt-secret-key --value "<seu-jwt-secret>"
```

- Use nomes **com hífens** no Key Vault.
- O backend faz o mapeamento para atributos com underscores automaticamente.
- Para múltiplos Key Vaults, defina as URLs nas variáveis de ambiente e crie os segredos em cada cofre conforme a tabela acima.
