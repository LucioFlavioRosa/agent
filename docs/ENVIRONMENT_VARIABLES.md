# Variáveis de Ambiente do Projeto

Este documento lista **todas as variáveis de ambiente** necessárias para o funcionamento do projeto, detalhando sua finalidade, obrigatoriedade e exemplos de valores. Utilize este guia para configurar corretamente seu ambiente.

## Lista Completa de Variáveis

| Nome da Variável                         | Descrição                                                                 | Exemplo de Valor                                   | Obrigatória |
|------------------------------------------|---------------------------------------------------------------------------|----------------------------------------------------|-------------|
| REDIS_URL                               | URL de conexão do Redis para cache e filas.                              | `redis://localhost:6379/0`                         | Sim         |
| AZURE_KEY_VAULT_AZURE_INFRASTRUCTURE_URL | URL do Key Vault Azure de infraestrutura (armazenamento de secrets de infra). | `https://kv-infra-peers.vault.azure.net/`          | Sim         |
| AZURE_KEY_VAULT_LLM_URL                  | URL do Key Vault Azure para secrets de LLM (modelos, tokens, etc).        | `https://kv-llm-peers.vault.azure.net/`            | Sim         |
| AZURE_KEY_VAULT_GITHUB_URL               | URL do Key Vault Azure para secrets do GitHub.                            | `https://kv-github-peers.vault.azure.net/`         | Sim         |
| AZURE_KEY_VAULT_AZURE_DEVOPS_URL         | URL do Key Vault Azure para secrets do Azure DevOps.                      | `https://kv-azdo-peers.vault.azure.net/`           | Sim         |
| AZURE_MONGODB_DATABASE                   | Nome do banco de dados MongoDB utilizado para mapeamento de grupos.       | `mcp_groups_db`                                    | Sim         |
| AZURE_MONGODB_GROUP_COLLECTION           | Nome da collection do MongoDB que armazena o mapeamento de grupos.        | `user_group_mapping`                               | Sim         |

## Detalhes e Exemplos

### REDIS_URL
- **Descrição:** URL de conexão para o serviço Redis utilizado pelo projeto.
- **Exemplo:** `redis://localhost:6379/0`
- **Obrigatória:** Sim

### AZURE_KEY_VAULT_AZURE_INFRASTRUCTURE_URL
- **Descrição:** URL do Key Vault Azure responsável por secrets de infraestrutura (ex: connection strings de storage e MongoDB).
- **Exemplo:** `https://kv-infra-peers.vault.azure.net/`
- **Obrigatória:** Sim

### AZURE_KEY_VAULT_LLM_URL
- **Descrição:** URL do Key Vault Azure utilizado para armazenar secrets de provedores LLM (ex: AWS Bedrock, OpenAI).
- **Exemplo:** `https://kv-llm-peers.vault.azure.net/`
- **Obrigatória:** Sim

### AZURE_KEY_VAULT_GITHUB_URL
- **Descrição:** URL do Key Vault Azure para secrets de autenticação do GitHub.
- **Exemplo:** `https://kv-github-peers.vault.azure.net/`
- **Obrigatória:** Sim

### AZURE_KEY_VAULT_AZURE_DEVOPS_URL
- **Descrição:** URL do Key Vault Azure para secrets de autenticação do Azure DevOps.
- **Exemplo:** `https://kv-azdo-peers.vault.azure.net/`
- **Obrigatória:** Sim

### AZURE_MONGODB_DATABASE
- **Descrição:** Nome do banco de dados MongoDB utilizado para armazenar o mapeamento de grupos de usuários.
- **Exemplo:** `mcp_groups_db`
- **Obrigatória:** Sim

### AZURE_MONGODB_GROUP_COLLECTION
- **Descrição:** Nome da collection do MongoDB que armazena o mapeamento de grupos de usuários e empresas.
- **Exemplo:** `user_group_mapping`
- **Obrigatória:** Sim

## Observações Importantes
- Todas as variáveis acima são **obrigatórias** para o funcionamento correto do projeto.
- O nome do container do Blob Storage agora é construído dinamicamente para cada cliente no formato `azure-storage-container-name-{grupo}-{empresa}`. Não é mais necessário definir a variável `AZURE_STORAGE_CONTAINER_NAME` no ambiente.
- Os valores dos Key Vaults devem ser URLs válidas do serviço Azure Key Vault.
- O nome do container e os nomes de banco/collection devem ser previamente criados e configurados no Azure/MongoDB.

## Referência de Nomes
- Recomenda-se seguir o padrão de nomenclatura para variáveis de ambiente conforme exemplos acima.
