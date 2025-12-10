# Configuração de Cofres de Segredos e Variáveis de Ambiente

Este documento detalha a arquitetura de múltiplos Key Vaults, a leitura de variáveis de ambiente e o fluxo de carregamento de segredos para os provedores LLM (OpenAI e Claude).

## 1. Arquitetura de Cofres de Segredos

A solução utiliza múltiplos Azure Key Vaults para segregar segredos por finalidade:

- **AZURE_KV_URL**: Cofre para segredos gerais da Azure (ex: conexões de banco, storage, etc.)
- **DEVOPS_KV_URL**: Cofre para segredos de integração com Azure DevOps
- **GITHUB_KV_URL**: Cofre para segredos de integração com GitHub
- **LLM_KV_URL**: Cofre exclusivo para segredos de provedores LLM (ex: OpenAI, Anthropic Claude)

Cada cofre é identificado por sua URL, definida via variável de ambiente.

## 2. Configuração das Variáveis de Ambiente

As seguintes variáveis de ambiente devem ser definidas antes de iniciar a aplicação:

- `AZURE_KV_URL` (ex: `https://meu-cofre-azure.vault.azure.net/`)
- `DEVOPS_KV_URL` (ex: `https://meu-cofre-devops.vault.azure.net/`)
- `GITHUB_KV_URL` (ex: `https://meu-cofre-github.vault.azure.net/`)
- `LLM_KV_URL` (ex: `https://meu-cofre-llm.vault.azure.net/`)
- `AZURE_OPENAI_MODELS` (endpoint do Azure OpenAI, não é segredo)
- Outras variáveis de ambiente padrão (ex: REDIS_HOST, REDIS_PASSWORD, etc.)

> **Importante:** As URLs devem começar com `https://` e apontar para um Key Vault válido.

## 3. Convenção de Nomenclatura de Segredos

- **Azure Key Vault** recomenda o uso de hífens (`-`) em vez de underscores (`_`) nos nomes dos segredos.
- Exemplo: `azure-openai-modelos` em vez de `AZURE_OPENAI_MODELOS`.
- O código faz log de warning se um segredo for solicitado com underscores.

## 4. Fluxo de Leitura de Segredos

1. **Settings** (`core/config.py`):
   - Carrega as URLs dos cofres via variáveis de ambiente.
   - Disponibiliza métodos para validação e acesso aos cofres.

2. **AzureSecretManager** (`services/azure_secret_manager.py`):
   - Instanciado com um `vault_type` (enum: `azure`, `devops`, `github`, `llm`).
   - Usa a URL correspondente para criar um `SecretClient` autenticado via `DefaultAzureCredential`.
   - O método `get_secret(nome)` busca o segredo no cofre correto.

3. **LLMProviderFactory** (`services/factories/llm_provider_factory.py`):
   - Ao criar um provider LLM (OpenAI ou Claude), injeta um `AzureSecretManager(vault_type=VaultType.LLM)` como parâmetro `secret_manager`.
   - Todos os providers LLM passam a buscar suas credenciais exclusivamente no cofre LLM.

4. **Providers LLM** (`tools/requisicao_openai.py`, `tools/requisicao_claude.py`):
   - Recebem o `secret_manager` injetado e utilizam `get_secret` para buscar as chaves de API.
   - Não leem mais segredos diretamente de variáveis de ambiente.

### Diagrama de Sequência

mermaid
sequenceDiagram
    participant App
    participant Settings
    participant LLMProviderFactory
    participant AzureSecretManager
    participant KeyVault

    App->>Settings: Carrega variáveis de ambiente (URLs dos cofres)
    App->>LLMProviderFactory: Solicita provider LLM
    LLMProviderFactory->>AzureSecretManager: Instancia com vault_type=LLM
    AzureSecretManager->>KeyVault: Autentica e busca segredo (ex: ANTHROPICAPIKEY)
    KeyVault-->>AzureSecretManager: Retorna segredo
    AzureSecretManager-->>LLMProviderFactory: Retorna segredo
    LLMProviderFactory-->>App: Retorna provider LLM configurado


## 5. Exemplos de Uso

python
from services.factories.llm_provider_factory import LLMProviderFactory
from tools.rag_retriever import AzureAISearchRAGRetriever

provider = LLMProviderFactory.create_provider('claude-sonnet-4-5', rag_retriever=AzureAISearchRAGRetriever())
# provider já está configurado para buscar segredos no cofre LLM


## 6. Troubleshooting

- **Erro: URL do Key Vault não configurada**
  - Verifique se a variável de ambiente correspondente está definida e correta.
- **Erro: Falha de autenticação**
  - O serviço precisa ter permissão de acesso ao Key Vault (Managed Identity ou Service Principal).
- **Warning: Nome do segredo contém underscores**
  - Renomeie o segredo no Key Vault para usar hífens.
- **Segredo não encontrado**
  - Confirme o nome do segredo e o cofre correto.

## 7. Segurança

- Nenhum segredo é logado em texto claro.
- Exceções não expõem valores sensíveis.
- O acesso aos cofres é autenticado via `DefaultAzureCredential`.
- Falhas de configuração são detectadas rapidamente na inicialização.
