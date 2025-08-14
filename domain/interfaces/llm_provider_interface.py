from abc import ABC, abstractmethod
from typing import Any, Dict

class ILLMProvider(ABC):
    """
    Interface para provedores de Large Language Models (LLM).
    """
    @abstractmethod
    def executar_analise_llm(
        self,
        tipo_analise: str,
        codigo: str,
        analise_extra: str,
        usar_rag: bool,
        model_name: str,
        max_token_out: int
    ) -> Dict[str, Any]:
        """Executa a análise LLM e retorna o resultado no formato esperado."""
        pass
