from tools.requisicao_claude import AmazonBedrockProvider
from tools.requisicao_openai import OpenAILLMProvider
from services.azure_secret_manager import AzureSecretManager, VaultType

def create_provider(model_name=None, secret_manager=None, user_email=None, group_resolver=None):
    secret_manager = secret_manager or AzureSecretManager(vault_type=VaultType.LLM)
    # Seleção dinâmica do provedor LLM conforme model_name
    if model_name and 'gpt' in str(model_name).lower():
        provider = OpenAILLMProvider(secret_manager=secret_manager, user_email=user_email, group_resolver=group_resolver)
    else:
        provider = AmazonBedrockProvider(secret_manager=secret_manager, user_email=user_email, group_resolver=group_resolver)
    return provider
