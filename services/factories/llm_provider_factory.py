from tools.requisicao_claude import AmazonBedrockProvider
from services.azure_secret_manager import AzureSecretManager, VaultType

def create_provider(model_name=None, secret_manager=None, user_email=None, group_resolver=None):
    secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
    provider = AmazonBedrockProvider(secret_manager=secret_manager, user_email=user_email, group_resolver=group_resolver)
    return provider
