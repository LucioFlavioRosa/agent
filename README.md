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
  - Exemplos de secrets: `AWS-ACCESS-KEY-ID-usuario-empresa`, `AWS-SECRET-ACCESS-KEY-usuario-empresa`, `AWS-REGION-usuario-empresa`, secrets de OpenAI no formato `openai-token-usuario-empresa`.

- **Cofre de Repositórios (`VaultType.REPOSITORY`)**: Armazena tokens de acesso dos repositórios (GitHub, GitLab, Azure DevOps).
  - Variável de ambiente: `AZURE_KEY_VAULT_REPOSITORY_URL`
  - Exemplos de secrets: `github-token-usuario-empresa`, `gitlab-token-usuario-empresa`, `azure-token-usuario-empresa`.

- **Cofre de Blob Storage (`VaultType.BLOB_STORAGE`)**: Armazena secrets relacionados ao Blob Storage.
  - Variável de ambiente: `AZURE_KEY_VAULT_BLOB_STORAGE_URL`
  - Exemplos de secrets: `azure-storage-connection-string-usuario-empresa`.

> **Importante:** Todos os secrets devem seguir o padrão de nomenclatura: `nome-usuario-empresa`, onde `usuario` e `empresa` são extraídos do email do usuário executor (campo `usuario_executor` do payload). Por exemplo, para o email `lucio.rosa@peers.com`, o nome do secret será `github-lucio.rosa-peers`.

> **Não há fallback**: Se o secret com contexto de usuário não existir, a operação falhará. Não existe mais fallback para secrets sem contexto de usuário.

### Secrets AWS Necessários
- `AWS-ACCESS-KEY-ID-usuario-empresa`
- `AWS-SECRET-ACCESS-KEY-usuario-empresa`
- `AWS-REGION-usuario-empresa`

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
- Adicione os secrets listados acima, sempre usando o padrão `nome-usuario-empresa`.
- Não existe fallback: se o secret não for encontrado para o usuário, a operação falha.
- Valide que o `vault_type=VaultType.LLM` está configurado corretamente para apontar para o Key Vault de LLM.

### Referências
- [Documentação AWS Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [SDK boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
