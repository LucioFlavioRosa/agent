from typing import Optional, Dict, Type, Any
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from tools.requisicao_bedrock import AmazonBedrockProvider
from services.azure_secret_manager import AzureSecretManager, VaultType

class LLMProviderFactory:
    _providers: Dict[str, Type[ILLMProvider]] = {
        'openai': OpenAILLMProvider,
        'anthropic': AnthropicClaudeProvider,
        'claude': AnthropicClaudeProvider
    }
    
    @classmethod
    def create_provider(
        cls,
        context: Any,
        model_name: Optional[str] = None,
        provider_hint: Optional[str] = None,
        bedrock_enabled: bool = False
    ) -> ILLMProvider:
        model_lower = (model_name or "").lower()
        secret_manager = AzureSecretManager(vault_type=VaultType.LLM)
        provider_class = None
        if bedrock_enabled:
            if provider_hint:
                hint_lower = provider_hint.lower()
                if hint_lower == "anthropic" or "claude" in model_lower:
                    provider_class = AmazonBedrockProvider
            elif "claude" in model_lower:
                provider_class = AmazonBedrockProvider
        if not provider_class:
            if provider_hint:
                hint_lower = provider_hint.lower()
                if hint_lower == "anthropic":
                    provider_class = cls._providers.get('anthropic', AnthropicClaudeProvider)
                elif hint_lower == "openai":
                    provider_class = cls._providers.get('openai', OpenAILLMProvider)
            if not provider_class:
                if "claude" in model_lower:
                    provider_class = cls._providers.get('claude', AnthropicClaudeProvider)
                else:
                    provider_class = cls._providers.get('openai', OpenAILLMProvider)
        return provider_class(secret_manager=secret_manager)
    
    @classmethod
    def register_provider(cls, key: str, provider_class: Type[ILLMProvider]) -> None:
        cls._providers[key] = provider_class
