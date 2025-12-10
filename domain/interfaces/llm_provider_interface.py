from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ILLMProvider(ABC):
    @abstractmethod
    def executar_prompt(
        self,
        tipo_tarefa: str,          
        prompt_principal: str,   
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        job_id: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        pass

class ILLMProviderComplete(ILLMProvider):
    @abstractmethod
    def executar_prompt_com_rag(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        job_id: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def executar_prompt_com_modelo(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        model_name: Optional[str] = None,
        job_id: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        pass
