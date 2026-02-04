# Exemplos de Secrets e Variáveis de Ambiente

Este documento detalha quais variáveis precisam ser configuradas como variáveis de ambiente e quais devem estar nos cofres (Key Vaults), além de exemplos concretos de nomes de secrets para diferentes cenários de usuário, grupo e empresa.

## Variáveis de Ambiente Obrigatórias

Estas variáveis devem estar presentes no ambiente do sistema:

- `AZURE_KEY_VAULT_LLM_URL`: URL do Key Vault de LLM
- `AZURE_KEY_VAULT_REPOSITORY_URL`: URL do Key Vault de repositórios
- `AZURE_KEY_VAULT_BLOB_STORAGE_URL`: URL do Key Vault de Blob Storage
- `MONGODB_CONNECTION_STRING_SECRET_NAME`: Nome do secret no Key Vault que contém a connection string do MongoDB
- `MONGODB_DATABASE_NAME`: Nome do banco de dados MongoDB
- `MONGODB_COLLECTION_NAME`: Nome da collection de mapeamento de grupos no MongoDB
- `REDIS_HOST`: Host do Redis
- `REDIS_PORT`: Porta do Redis

## Secrets nos Key Vaults

Os secrets devem ser criados nos Key Vaults correspondentes, seguindo o padrão de nomenclatura:

`nome-grupo-empresa`

Onde:
- `nome`: tipo do secret (ex: github-token, AWS-ACCESS-KEY-ID, azure-storage-connection-string)
- `grupo`: grupo do usuário, obtido via consulta ao MongoDB
- `empresa`: empresa do usuário

### Exemplos Concretos

#### Exemplo 1: Usuário GitHub
- **Usuário:** lucio.rosa@peers.com
- **Grupo:** grupo
- **Empresa:** peers
- **Secrets:**
  - `github-token-grupo-peers` (Key Vault de Repositórios)
  - `AWS-ACCESS-KEY-ID-grupo-peers` (Key Vault de LLM)
  - `AWS-SECRET-ACCESS-KEY-grupo-peers` (Key Vault de LLM)
  - `AWS-REGION-grupo-peers` (Key Vault de LLM)
  - `azure-storage-connection-string-grupo-peers` (Key Vault de Blob Storage)

#### Exemplo 2: Usuário Azure DevOps
- **Usuário:** maria.silva@acme.com
- **Grupo:** dev
- **Empresa:** acme
- **Secrets:**
  - `azure-token-dev-acme` (Key Vault de Repositórios)
  - `AWS-ACCESS-KEY-ID-dev-acme` (Key Vault de LLM)
  - `AWS-SECRET-ACCESS-KEY-dev-acme` (Key Vault de LLM)
  - `AWS-REGION-dev-acme` (Key Vault de LLM)
  - `azure-storage-connection-string-dev-acme` (Key Vault de Blob Storage)

#### Exemplo 3: Usuário GitLab
- **Usuário:** joao.pereira@startup.com
- **Grupo:** squad1
- **Empresa:** startup
- **Secrets:**
  - `gitlab-token-squad1-startup` (Key Vault de Repositórios)
  - `AWS-ACCESS-KEY-ID-squad1-startup` (Key Vault de LLM)
  - `AWS-SECRET-ACCESS-KEY-squad1-startup` (Key Vault de LLM)
  - `AWS-REGION-squad1-startup` (Key Vault de LLM)
  - `azure-storage-connection-string-squad1-startup` (Key Vault de Blob Storage)

## Resumo dos Nomes de Variáveis e Secrets

### Variáveis de Ambiente:
- AZURE_KEY_VAULT_LLM_URL
- AZURE_KEY_VAULT_REPOSITORY_URL
- AZURE_KEY_VAULT_BLOB_STORAGE_URL
- MONGODB_CONNECTION_STRING_SECRET_NAME
- MONGODB_DATABASE_NAME
- MONGODB_COLLECTION_NAME
- REDIS_HOST
- REDIS_PORT

### Secrets (Key Vaults):
- github-token-<grupo>-<empresa>
- gitlab-token-<grupo>-<empresa>
- azure-token-<grupo>-<empresa>
- openai-token-<grupo>-<empresa>
- AWS-ACCESS-KEY-ID-<grupo>-<empresa>
- AWS-SECRET-ACCESS-KEY-<grupo>-<empresa>
- AWS-REGION-<grupo>-<empresa>
- azure-storage-connection-string-<grupo>-<empresa>

> **Nota:** O grupo é sempre obtido via consulta ao serviço MongoDBGroupResolverService. Não existe fallback: se o grupo não for encontrado, a operação falha.
