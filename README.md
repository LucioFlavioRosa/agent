# Projeto: Integração LLM via Amazon Bedrock

## Mudança de Provedor LLM

A arquitetura do projeto foi atualizada para utilizar o Amazon Bedrock como provedor LLM, substituindo a integração direta com Anthropic Claude.

### Nova Arquitetura
- Utiliza o SDK boto3 para invocação do Bedrock Runtime.
- O provedor é implementado em `tools/requisicao_claude.py` como `AmazonBedrockProvider`.
- Os secrets AWS são recuperados via `AzureSecretManager` (Key Vault), usando o `vault_type=VaultType.LLM`.

### Segregação de Cofres (Key Vaults)
Para garantir segurança e organização, os secrets são segregados em cofres distintos:

- **Cofre de LLM (`VaultType.LLM`)**: Armazena tokens e endereços de acesso às APIs de LLM, como OpenAI e AWS Bedrock.
  - Variável de ambiente: `AZURE_KEY_VAULT_LLM_URL`
  - Exemplos de secrets: `AWS-ACCESS-KEY-ID-grupo-peers`, `AWS-SECRET-ACCESS-KEY-grupo-peers`, `AWS-REGION-grupo-peers`, secrets de OpenAI no formato `openai-token-grupo-peers`.

- **Cofre de Repositórios (`VaultType.REPOSITORY`)**: Armazena tokens de acesso dos repositórios (GitHub, GitLab, Azure DevOps).
  - Variável de ambiente: `AZURE_KEY_VAULT_REPOSITORY_URL`
  - Exemplos de secrets: `github-token-grupo-peers`, `gitlab-token-grupo-peers`, `azure-token-grupo-peers`.

- **Cofre de Blob Storage (`VaultType.BLOB_STORAGE`)**: Armazena secrets relacionados ao Blob Storage.
  - Variável de ambiente: `AZURE_KEY_VAULT_BLOB_STORAGE_URL`
  - Exemplos de secrets: `azure-storage-connection-string-grupo-peers`.

> **Importante:** Todos os secrets devem seguir o padrão de nomenclatura: `nome-grupo-empresa`, onde `grupo` é obtido via consulta ao serviço `MongoDBGroupResolverService` que acessa o MongoDB configurado. O serviço consulta o mapeamento de grupos para o usuário e empresa informados, retornando o grupo correspondente. Por exemplo, para o email `lucio.rosa@peers.com`, o serviço consulta o MongoDB para obter o grupo do usuário `lucio.rosa` na empresa `peers`, e o nome do secret será `github-token-grupo-peers`.

> **Não há fallback**: Se o mapeamento de grupo não existir no MongoDB para o usuário/empresa, a operação falhará. Não existe mais fallback para secrets sem contexto de grupo.

### Serviço de Resolução de Grupo
- O serviço `MongoDBGroupResolverService` é responsável por consultar o MongoDB da Azure para obter o grupo do usuário e empresa informados.
- O MongoDB deve conter uma collection com o mapeamento `{ "usuario": "lucio.rosa", "empresa": "peers", "grupo": "grupo" }`.
- O nome do secret será sempre montado como `nome-grupo-empresa`.

### Secrets AWS Necessários
- `AWS-ACCESS-KEY-ID-grupo-peers`
- `AWS-SECRET-ACCESS-KEY-grupo-peers`
- `AWS-REGION-grupo-peers`

Estes secrets devem ser configurados no Azure Key Vault de LLM utilizado pelo projeto, seguindo o padrão acima.

### Exemplo de Configuração de Model ID
- O modelo padrão utilizado é: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- Para usar outros modelos Bedrock, basta informar o `model_name` correspondente ao chamar o provider.

### Roteamento Cross-Region
- O prefixo `us.` no model_id habilita roteamento inteligente entre regiões AWS.
- Recomenda-se sempre usar o prefixo para máxima disponibilidade.

### Adicionando Novos Modelos Bedrock
- Consulte a documentação AWS Bedrock para obter o model_id de novos modelos.
- Adicione o model_id desejado ao parâmetro `model_name` ao invocar o provider.

### Testes de Integração
- Testes reais de comunicação com Bedrock estão em `tests/integration/test_bedrock_integration.py`.
- Os testes validam invocação, fallback de modelo, concatenação de instruções extras e estrutura da resposta.

### Configuração de Secrets no Azure Key Vault
- Adicione os secrets listados acima, sempre usando o padrão `nome-grupo-empresa`.
- Não existe fallback: se o mapeamento de grupo não for encontrado no MongoDB, a operação falha.
- Valide que o `vault_type=VaultType.LLM` está configurado corretamente para apontar para o Key Vault de LLM.

### Variáveis de Ambiente para MongoDB
- `MONGODB_CONNECTION_STRING_SECRET_NAME`: Nome do secret no Key Vault que contém a connection string do MongoDB.
- `MONGODB_DATABASE_NAME`: Nome do banco de dados MongoDB onde está o mapeamento de grupos.
- `MONGODB_COLLECTION_NAME`: Nome da collection do MongoDB que armazena o mapeamento de grupos.

### Referências
- [Documentação AWS Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [SDK boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
