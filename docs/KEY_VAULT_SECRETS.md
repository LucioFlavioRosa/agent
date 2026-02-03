# Secrets nos Key Vaults Azure

Este documento detalha **todos os secrets** que devem ser configurados nos Key Vaults Azure do projeto, organizados por cofre (vault) e com exemplos de nomes e valores. O padrão de nomenclatura é `{nome}-{grupo}-{empresa}`.

## Padrão de Nomenclatura
- Todos os secrets seguem o padrão: `{nome}-{grupo}-{empresa}`
- Exemplo: `github-token-grupo-peers`
- O valor de `grupo` é obtido via consulta ao serviço `MongoDBGroupResolverService` no MongoDB.
- O valor de `empresa` corresponde ao domínio do usuário (ex: `peers`).

## Cofres e seus Secrets

### 1. Cofre de Infraestrutura Azure (`VaultType.AZURE_INFRASTRUCTURE`)

| Nome do Secret                                  | Descrição                                         | Exemplo de Nome                           | Exemplo de Valor                  |
|-------------------------------------------------|---------------------------------------------------|-------------------------------------------|------------------------------------|
| azure-storage-connection-string-{grupo}-{empresa}| Connection string do Blob Storage Azure           | `azure-storage-connection-string-grupo-peers` | `DefaultEndpointsProtocol=https;AccountName=...` |
| azure-mongodb-connection-string                  | Connection string do MongoDB                      | `azure-mongodb-connection-string`          | `mongodb+srv://user:pass@cluster.mongodb.net/db` |

### 2. Cofre de LLM (`VaultType.LLM`)

| Nome do Secret                                  | Descrição                                         | Exemplo de Nome                           | Exemplo de Valor                  |
|-------------------------------------------------|---------------------------------------------------|-------------------------------------------|------------------------------------|
| AWS-ACCESS-KEY-ID-{grupo}-{empresa}             | AWS Access Key para Bedrock                       | `AWS-ACCESS-KEY-ID-grupo-peers`           | `AKIAIOSFODNN7EXAMPLE`            |
| AWS-SECRET-ACCESS-KEY-{grupo}-{empresa}         | AWS Secret Key para Bedrock                       | `AWS-SECRET-ACCESS-KEY-grupo-peers`       | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| AWS-REGION-{grupo}-{empresa}                    | Região AWS para Bedrock                           | `AWS-REGION-grupo-peers`                  | `us-east-1`                       |
| openai-token-{grupo}-{empresa}                  | Token de acesso OpenAI (se aplicável)             | `openai-token-grupo-peers`                | `sk-abc123...`                    |

### 3. Cofre GitHub (`VaultType.GITHUB`)

| Nome do Secret                                  | Descrição                                         | Exemplo de Nome                           | Exemplo de Valor                  |
|-------------------------------------------------|---------------------------------------------------|-------------------------------------------|------------------------------------|
| github-token-{grupo}-{empresa}                  | Token de acesso GitHub                            | `github-token-grupo-peers`                | `ghp_16charactertokenexample`      |

### 4. Cofre Azure DevOps (`VaultType.AZURE_DEVOPS`)

| Nome do Secret                                  | Descrição                                         | Exemplo de Nome                           | Exemplo de Valor                  |
|-------------------------------------------------|---------------------------------------------------|-------------------------------------------|------------------------------------|
| azure-token-{grupo}-{empresa}                   | Token de acesso Azure DevOps                      | `azure-token-grupo-peers`                 | `azdo_16charactertokenexample`     |

## Exemplos Concretos

- Para o usuário `lucio.rosa@peers.com` cujo grupo é `grupo`:
  - GitHub: `github-token-grupo-peers`
  - Bedrock AWS Access Key: `AWS-ACCESS-KEY-ID-grupo-peers`
  - Blob Storage: `azure-storage-connection-string-grupo-peers`

## Observações Importantes
- **Todos os secrets devem ser criados previamente** nos respectivos cofres.
- O nome do secret deve sempre incluir o grupo e empresa, obtidos via serviço de mapeamento no MongoDB.
- Não existe fallback: se o mapeamento de grupo não existir, a operação falha.
- Os valores dos secrets devem ser strings válidas para autenticação nos respectivos serviços.

## Resumo dos Cofres
- **VaultType.AZURE_INFRASTRUCTURE**: Secrets de infraestrutura (Blob Storage, MongoDB)
- **VaultType.LLM**: Secrets de provedores LLM (AWS Bedrock, OpenAI)
- **VaultType.GITHUB**: Token de acesso GitHub
- **VaultType.AZURE_DEVOPS**: Token de acesso Azure DevOps

## Referências
- [Documentação Azure Key Vault](https://learn.microsoft.com/pt-br/azure/key-vault/general/)
- [Documentação AWS Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/)
