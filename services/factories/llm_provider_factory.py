from tools.requisicao_claude import AmazonBedrockProvider
from services.azure_secret_manager import AzureSecretManager, VaultType

def create_provider(model_name=None, rag_retriever=None, secret_manager=None):
    # O secret_manager pode ser passado ou será criado com vault_type LLM
    secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
    # Instancia o AmazonBedrockProvider
    provider = AmazonBedrockProvider(secret_manager=secret_manager)
    # O rag_retriever não é utilizado diretamente no BedrockProvider, mas pode ser passado para futuras extensões
    return provider
