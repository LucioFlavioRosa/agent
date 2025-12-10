from typing import Optional, Dict, Type
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from tools.rag_retriever import AzureAISearchRAGRetriever
from services.azure_secret_manager import AzureSecretManager, VaultType

class LLMProviderFactory:
    _providers: Dict[str, Type[ILLMProvider]] = {
        'openai': OpenAILLMProvider,
        'claude': AnthropicClaudeProvider
    }
    
    @classmethod
    def create_provider(cls, model_name: Optional[str], rag_retriever: AzureAISearchRAGRetriever) -> ILLMProvider:
        model_lower = (model_name or "").lower()
        secret_manager = AzureSecretManager(vault_type=VaultType.LLM)
        if "claude" in model_lower:
            provider_class = cls._providers.get('claude', OpenAILLMProvider)
        else:
            provider_class = cls._providers.get('openai', OpenAILLMProvider)
        return provider_class(rag_retriever=rag_retriever, secret_manager=secret_manager)
    
    @classmethod
    def register_provider(cls, key: str, provider_class: Type[ILLMProvider]) -> None:
        cls._providers[key] = provider_class
