from typing import Optional
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.requisicao_openai import OpenAIProvider
from tools.requisicao_claude import ClaudeProvider

class LLMProviderFactory:
    @staticmethod
    def create_provider(model_name: Optional[str], rag_retriever=None) -> ILLMProvider:
        if model_name is None:
            # Default para OpenAI
            return OpenAIProvider(rag_retriever=rag_retriever)
        model_name_lower = model_name.lower()
        if 'openai' in model_name_lower or 'gpt' in model_name_lower:
            return OpenAIProvider(rag_retriever=rag_retriever, model_name=model_name)
        elif 'claude' in model_name_lower or 'anthropic' in model_name_lower:
            return ClaudeProvider(rag_retriever=rag_retriever, model_name=model_name)
        else:
            # Fallback para OpenAI
            return OpenAIProvider(rag_retriever=rag_retriever, model_name=model_name)
