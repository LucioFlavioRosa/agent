from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ILLMProvider(ABC):
    """
    Interface base para provedores de Large Language Models (LLM).
    
    Contrato de Implementação:
    - Implementações devem garantir thread-safety se usadas concorrentemente
    - Respostas devem ser estruturadas consistentemente
    - Erros de rede/API devem ser encapsulados em RuntimeError
    - Validação de parâmetros deve gerar ValueError
    """
    
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

class ILLMProviderWithRAG(ILLMProvider):
  
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

class ILLMProviderWithModelSelection(ILLMProvider):
    
    
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

class ILLMProviderComplete(ILLMProviderWithRAG, ILLMProviderWithModelSelection):
    
    
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
