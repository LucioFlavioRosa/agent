# Projeto: Integração LLM via Amazon Bedrock

## Mudança de Provedor LLM

A arquitetura do projeto foi atualizada para utilizar o Amazon Bedrock como provedor LLM, substituindo a integração direta com Anthropic Claude.

### Nova Arquitetura
- Utiliza o SDK boto3 para invocação do Bedrock Runtime.
- O provedor é implementado em `tools/requisicao_claude.py` como `AmazonBedrockProvider`.
- Os secrets AWS são recuperados via `AzureSecretManager` (Key Vault), usando o `vault_type=VaultType.LLM`.

### Secrets AWS Necessários
- `AWS-ACCESS-KEY-ID`
- `AWS-SECRET-ACCESS-KEY`
- `AWS-REGION`

Estes secrets devem ser configurados no Azure Key Vault utilizado pelo projeto. Certifique-se que o vault correto está sendo referenciado.

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
- Adicione os secrets listados acima.
- Valide que o `vault_type=VaultType.LLM` está configurado corretamente para apontar para o Key Vault de LLM.

### Referências
- [Documentação AWS Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [SDK boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
