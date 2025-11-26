from tools.requisicao_openai import OpenAILLMProvider
from tools.requisicao_claude import AnthropicClaudeProvider
from domain.interfaces.llm_provider_interface import ILLMProvider
from typing import Optional, Any

class LLMProviderFactory:
    @staticmethod
    def create_provider(model_name: Optional[str] = None, rag_retriever: Any = None):
        if model_name:
            if 'claude' in model_name.lower():
                return AnthropicClaudeProvider(rag_retriever=rag_retriever)
            else:
                return OpenAILLMProvider(rag_retriever=rag_retriever)
        return OpenAILLMProvider(rag_retriever=rag_retriever)
