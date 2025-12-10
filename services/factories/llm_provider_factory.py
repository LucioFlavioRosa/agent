from typing import Optional, Dict, Type, Any
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from services.azure_secret_manager import AzureSecretManager, VaultType

class LLMProviderFactory:
    _providers: Dict[str, Type[ILLMProvider]] = {
        'openai': OpenAILLMProvider,
        'claude': AnthropicClaudeProvider
    }
    
    @classmethod
    def create_provider(cls, context: Any, model_name: Optional[str] = None) -> ILLMProvider:
        """
        Cria uma instância do provedor de LLM.
        
        Args:
            context: O contexto ou tipo da análise (ex: 'financial', 'legal'). 
                     Adicionado para corrigir o erro de '3 arguments given'.
            model_name: O nome específico do modelo (ex: 'gpt-4', 'claude-3').
        """
        
        # Garante que model_name seja string para evitar erro no .lower() se vier None
        model_lower = (model_name or "").lower()
        
        secret_manager = AzureSecretManager(vault_type=VaultType.LLM)
        
        # Lógica de seleção
        if "claude" in model_lower:
            provider_class = cls._providers.get('claude', OpenAILLMProvider)
        else:
            provider_class = cls._providers.get('openai', OpenAILLMProvider)
            
        return provider_class(secret_manager=secret_manager)
    
    @classmethod
    def register_provider(cls, key: str, provider_class: Type[ILLMProvider]) -> None:
        cls._providers[key] = provider_class
