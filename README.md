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

- **Cofre de Blob Storage (`VaultType.BLOB_STORAGE` / `VaultType.AZURE_INFRASTRUCTURE`)**: Armazena secrets relacionados ao Blob Storage.
  - Variável de ambiente: `AZURE_KEY_VAULT_BLOB_STORAGE_URL`
  - **Nome do container:** Agora o nome do container é recuperado dinamicamente do Key Vault de infraestrutura via secret `azure-storage-container-name-{grupo}-{empresa}`. Não é mais montado como string literal.
    - Exemplo de configuração do secret:
      - Nome do secret: `azure-storage-container-name-grupo-peers`
      - Valor do secret: `container-grupo-peers`
  - Exemplo de secret fixo: `azure-storage-connection-string` (fixo para todo o projeto).

> **Importante:** O nome do secret para a connection string do Blob Storage continua **fixo**: `azure-storage-connection-string`. Não há mais contextualização por grupo ou empresa para o secret de conexão.

> **Containers dinâmicos por cliente:** Cada cliente possui um container próprio no Blob Storage. O nome do container é obtido dinamicamente do Key Vault de infraestrutura (`VaultType.AZURE_INFRASTRUCTURE`) usando o secret `azure-storage-container-name-{grupo}-{empresa}`. O grupo é obtido via consulta ao serviço `MongoDBGroupResolverService` que acessa o MongoDB configurado. O serviço consulta o mapeamento de grupos para o usuário e empresa informados, retornando o grupo correspondente. Por exemplo, para o email `lucio.rosa@peers.com`, o serviço consulta o MongoDB para obter o grupo do usuário `lucio.rosa` na empresa `peers`, e o nome do secret será `azure-storage-container-name-grupo-peers`.

> **Não há fallback**: Se o mapeamento de grupo não existir no MongoDB para o usuário/empresa, a operação falhará. Não existe mais fallback para secrets sem contexto de grupo.

### Serviço de Resolução de Grupo
- O serviço `MongoDBGroupResolverService` é responsável por consultar o MongoDB da Azure para obter o grupo do usuário e empresa informados.
- O MongoDB deve conter uma collection com o mapeamento `{ "usuario": "lucio.rosa", "empresa": "peers", "grupo": "grupo" }`.
- O nome do secret do container será sempre montado como `azure-storage-container-name-{grupo}-{empresa}` e seu valor deve ser o nome real do container.

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
- Adicione os secrets listados acima, sempre usando o padrão `nome-grupo-empresa` para LLM e repositórios, e `azure-storage-connection-string` para Blob Storage.
- Para o nome do container, crie o secret `azure-storage-container-name-{grupo}-{empresa}` no Key Vault de infraestrutura e defina seu valor como o nome real do container.
- Não existe fallback: se o mapeamento de grupo não for encontrado no MongoDB, a operação falha.
- Valide que o `vault_type=VaultType.LLM` está configurado corretamente para apontar para o Key Vault de LLM.

### Variáveis de Ambiente para MongoDB
- `MONGODB_CONNECTION_STRING_SECRET_NAME`: Nome do secret no Key Vault que contém a connection string do MongoDB.
- `MONGODB_DATABASE_NAME`: Nome do banco de dados MongoDB onde está o mapeamento de grupos.
- `MONGODB_COLLECTION_NAME`: Nome da collection do MongoDB que armazena o mapeamento de grupos.

### Nova Funcionalidade: Verificação de Relatório Existente no Blob Storage

A primeira operação do fluxo de análise agora segue a seguinte sequência de eventos para garantir eficiência e evitar processamento desnecessário:

1. **Envio do Payload Inicial**
   - O usuário envia o payload inicial contendo os parâmetros da análise (exemplo: tipo de repositório, nome do repositório, branch, tipo de análise, instruções extras, usuário executor, etc).

2. **Geração do job_id**
   - O sistema gera um identificador único (`job_id`) para a análise.

3. **Verificação de Relatório Existente no Blob Storage**
   - Antes de iniciar qualquer processamento, o sistema consulta o Blob Storage para verificar se já existe um relatório para o mesmo contexto (projeto, análise, repositório, branch, usuário, etc).

4. **Retorno Imediato do Relatório Existente**
   - Se um relatório já existir no Blob Storage, ele é lido e retornado imediatamente ao usuário, evitando reprocessamento.

5. **Carregamento do Prompt**
   - Caso não exista relatório, o sistema carrega o arquivo de prompt correspondente à tarefa (por exemplo, via função `carregar_prompt(tipo_tarefa)`).

6. **Concatenação do Prompt com Instruções Extras**
   - O prompt carregado é concatenado com as instruções extras fornecidas pelo usuário no payload.

7. **Envio para o LLM**
   - O conteúdo resultante é enviado ao provedor LLM (Amazon Bedrock ou OpenAI, conforme configuração) para geração do relatório.

8. **Retorno do Relatório Gerado**
   - O relatório gerado pela LLM é retornado ao usuário e salvo no Blob Storage para futuras consultas.

#### Parâmetros Necessários no Payload
- `repository_type`: Tipo do repositório (github, gitlab, azure)
- `repo_name`: Nome do repositório
- `branch_name`: Nome da branch
- `analysis_type`: Tipo de análise
- `instrucoes_extras`: Instruções adicionais para o agente
- `usuario_executor`: Email do usuário executor
- Outros campos opcionais conforme necessidade

#### Observações Importantes
- O sistema prioriza a reutilização de relatórios existentes para otimizar recursos e tempo.
- O fluxo é transparente para o usuário: se o relatório já existe, ele é retornado; caso contrário, é gerado conforme instruções e prompt.
- O nome e contexto do relatório no Blob Storage são derivados dos parâmetros do payload e do mapeamento de grupo do usuário.

### Referências
- [Documentação AWS Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [SDK boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
