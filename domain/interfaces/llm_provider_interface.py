from abc import ABC, abstractmethod
from typing import Any, Dict

class ILLMProvider(ABC):
    """
    Interface para provedores de Large Language Models (LLM).
    """
    @abstractmethod
    def executar_prompt(
        self,
        tipo_tarefa: str,          
        prompt_principal: str,   
        instrucoes_extras: str,
        usar_rag: bool,
        model_name: str,
        max_token_out: int
    ) -> Dict[str, Any]:
        """Executa uma tarefa genérica no LLM e retorna o resultado."""
        pass
