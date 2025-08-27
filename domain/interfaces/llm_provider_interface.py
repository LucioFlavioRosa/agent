from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ILLMProvider(ABC):
    """
    Interface base para provedores de Large Language Models (LLM).
    
    Esta interface define o contrato básico para comunicação com diferentes
    provedores de LLM (OpenAI, Anthropic, etc.), garantindo consistência
    na execução de prompts e tratamento de respostas.
    
    A interface é segregada em métodos específicos para evitar parâmetros
    irrelevantes e seguir o princípio da segregação de interfaces (ISP).
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
        """
        Executa uma tarefa básica no LLM e retorna o resultado estruturado.
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa a ser executada (ex: 'refatoracao', 'analise')
            prompt_principal (str): Conteúdo principal do prompt, geralmente o código a ser analisado
            instrucoes_extras (str, optional): Instruções adicionais do usuário. Padrão é string vazia
            usar_rag (bool, optional): Se deve usar Retrieval-Augmented Generation. Padrão é False
            model_name (Optional[str], optional): Nome específico do modelo a usar. Se None, usa padrão
            max_token_out (int, optional): Máximo de tokens na resposta. Padrão é 15000
        
        Returns:
            Dict[str, Any]: Dicionário com a resposta estruturada contendo:
                - reposta_final (str): Resposta principal do LLM
                - tokens_entrada (int): Número de tokens consumidos na entrada
                - tokens_saida (int): Número de tokens gerados na saída
        
        Raises:
            ValueError: Se tipo_tarefa não for suportado ou parâmetros inválidos
            RuntimeError: Se houver falha na comunicação com o LLM
            TimeoutError: Se a requisição exceder o tempo limite
        """
        pass

class ILLMProviderWithRAG(ILLMProvider):
    """
    Interface estendida para provedores que suportam RAG (Retrieval-Augmented Generation).
    
    Esta interface segrega funcionalidades específicas de RAG, permitindo que
    implementações que não suportam RAG não precisem implementar métodos desnecessários.
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
        """
        Executa uma tarefa no LLM com suporte específico a RAG.
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa a ser executada
            prompt_principal (str): Conteúdo principal do prompt
            instrucoes_extras (str, optional): Instruções adicionais. Padrão é string vazia
            usar_rag (bool, optional): Flag para ativar RAG. Padrão é False
            max_token_out (int, optional): Máximo de tokens na resposta. Padrão é 15000
        
        Returns:
            Dict[str, Any]: Resposta estruturada com contexto RAG incorporado
        
        Raises:
            ValueError: Se não conseguir recuperar contexto RAG relevante
            RuntimeError: Se houver falha na comunicação com LLM ou sistema RAG
        """
        pass

class ILLMProviderWithModelSelection(ILLMProvider):
    """
    Interface estendida para provedores que suportam seleção específica de modelo.
    
    Esta interface segrega funcionalidades de seleção de modelo, permitindo
    flexibilidade na escolha de diferentes modelos para diferentes tarefas.
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
        """
        Executa uma tarefa no LLM com seleção específica de modelo.
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa a ser executada
            prompt_principal (str): Conteúdo principal do prompt
            instrucoes_extras (str, optional): Instruções adicionais. Padrão é string vazia
            model_name (Optional[str], optional): Nome específico do modelo. Se None, usa padrão
            max_token_out (int, optional): Máximo de tokens na resposta. Padrão é 15000
        
        Returns:
            Dict[str, Any]: Resposta estruturada do modelo especificado
        
        Raises:
            ValueError: Se model_name não for suportado pelo provedor
            RuntimeError: Se houver falha na comunicação com o modelo específico
        """
        pass

class ILLMProviderComplete(ILLMProviderWithRAG, ILLMProviderWithModelSelection):
    """
    Interface completa que combina todas as funcionalidades disponíveis.
    
    Esta interface é destinada a provedores que suportam todas as features:
    - Execução básica de prompts
    - Retrieval-Augmented Generation (RAG)
    - Seleção específica de modelos
    
    Implementações desta interface devem fornecer suporte completo a todas
    as funcionalidades, garantindo máxima flexibilidade de uso.
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
        """
        Executa uma tarefa completa no LLM com todas as funcionalidades disponíveis.
        
        Este método unifica todas as capacidades do provedor, permitindo uso
        simultâneo de RAG, seleção de modelo e configurações avançadas.
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa a ser executada
            prompt_principal (str): Conteúdo principal do prompt
            instrucoes_extras (str, optional): Instruções adicionais. Padrão é string vazia
            usar_rag (bool, optional): Se deve usar RAG. Padrão é False
            model_name (Optional[str], optional): Modelo específico. Se None, usa padrão
            max_token_out (int, optional): Máximo de tokens na resposta. Padrão é 15000
        
        Returns:
            Dict[str, Any]: Resposta estruturada com todas as funcionalidades aplicadas
        
        Raises:
            ValueError: Se parâmetros forem inválidos ou incompatíveis
            RuntimeError: Se houver falha em qualquer componente (LLM, RAG, etc.)
            TimeoutError: Se a requisição exceder o tempo limite
        """
        pass