from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ILLMProvider(ABC):
    """
    Interface base para provedores de Large Language Models (LLM).
    Segregada em métodos específicos para evitar parâmetros irrelevantes.
    """
    @abstractmethod
    def executar_prompt(
        self,
        tipo_tarefa: str,          
        prompt_principal: str,   
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """Executa uma tarefa básica no LLM e retorna o resultado."""
        pass

class ILLMProviderWithRAG(ILLMProvider):
    """
    Interface estendida para provedores que suportam RAG.
    Segrega funcionalidades específicas de RAG.
    """
    @abstractmethod
    def executar_prompt_com_rag(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """Executa uma tarefa no LLM com suporte a RAG."""
        pass

class ILLMProviderWithModelSelection(ILLMProvider):
    """
    Interface estendida para provedores que suportam seleção de modelo.
    Segrega funcionalidades específicas de seleção de modelo.
    """
    @abstractmethod
    def executar_prompt_com_modelo(
        self,
        tipo_tarefa: str,
        prompt_principal: str,
        instrucoes_extras: str = "",
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """Executa uma tarefa no LLM com seleção específica de modelo."""
        pass

class ILLMProviderComplete(ILLMProviderWithRAG, ILLMProviderWithModelSelection):
    """
    Interface completa que combina todas as funcionalidades.
    Para provedores que suportam todas as features.
    """
    @abstractmethod
    def executar_prompt(
        self,
        tipo_tarefa: str,          
        prompt_principal: str,   
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """Executa uma tarefa completa no LLM com todas as funcionalidades."""
        pass