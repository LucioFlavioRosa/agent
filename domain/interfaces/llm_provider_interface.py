from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ILLMProvider(ABC):
    """
    Interface base para provedores de Large Language Models (LLM).
    
    Esta interface define o contrato básico para interação com provedores de LLM,
    seguindo o princípio da segregação de interfaces para evitar dependências
    desnecessárias. Implementações devem fornecer funcionalidade básica de
    execução de prompts.
    
    Example:
        >>> provider = OpenAILLMProvider()
        >>> resultado = provider.executar_prompt(
        ...     tipo_tarefa="code_review",
        ...     prompt_principal="def hello(): pass",
        ...     instrucoes_extras="Analise este código Python"
        ... )
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
        
        Este método é a interface principal para comunicação com o LLM.
        Implementações devem carregar o prompt apropriado baseado no tipo_tarefa
        e processar a resposta de forma consistente.
        
        Args:
            tipo_tarefa (str): Identificador do tipo de análise (ex: "code_review", "refatoracao").
                Usado para carregar o prompt template apropriado.
            prompt_principal (str): Conteúdo principal a ser analisado (código, texto, JSON).
            instrucoes_extras (str, optional): Instruções adicionais do usuário. Defaults to "".
            usar_rag (bool, optional): Se deve usar Retrieval-Augmented Generation. Defaults to False.
            model_name (Optional[str], optional): Nome específico do modelo. Defaults to None (usa padrão).
            max_token_out (int, optional): Limite máximo de tokens na resposta. Defaults to 15000.
        
        Returns:
            Dict[str, Any]: Resultado estruturado contendo pelo menos:
                - reposta_final (str): Resposta principal do LLM
                - tokens_entrada (int, optional): Tokens consumidos na entrada
                - tokens_saida (int, optional): Tokens gerados na saída
        
        Raises:
            ValueError: Se tipo_tarefa for inválido ou prompt_principal estiver vazio.
            RuntimeError: Se houver falha na comunicação com o provedor LLM.
            FileNotFoundError: Se o template de prompt para tipo_tarefa não for encontrado.
            ConnectionError: Se houver problemas de conectividade com a API.
        
        Example:
            >>> resultado = provider.executar_prompt(
            ...     tipo_tarefa="security_audit",
            ...     prompt_principal='{"code": "SELECT * FROM users"}',
            ...     instrucoes_extras="Verificar SQL injection",
            ...     usar_rag=True,
            ...     max_token_out=8000
            ... )
            >>> print(resultado["reposta_final"])
        """
        pass

class ILLMProviderWithRAG(ILLMProvider):
    """
    Interface estendida para provedores que suportam Retrieval-Augmented Generation.
    
    Esta interface segrega funcionalidades específicas de RAG, permitindo que
    implementações que não suportam RAG não precisem implementar métodos
    desnecessários. RAG permite enriquecer prompts com contexto relevante
    obtido de bases de conhecimento externas.
    
    Example:
        >>> provider = OpenAIWithRAGProvider()
        >>> resultado = provider.executar_prompt_com_rag(
        ...     tipo_tarefa="compliance_check",
        ...     prompt_principal="function validateUser() {}",
        ...     usar_rag=True
        ... )
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
        
        Este método especializado permite implementações otimizadas para RAG,
        onde o contexto adicional é obtido de sistemas de busca semântica
        ou bases de conhecimento específicas da organização.
        
        Args:
            tipo_tarefa (str): Tipo de análise a ser realizada.
            prompt_principal (str): Conteúdo principal para análise.
            instrucoes_extras (str, optional): Instruções adicionais. Defaults to "".
            usar_rag (bool, optional): Flag para ativar RAG. Defaults to False.
            max_token_out (int, optional): Limite de tokens na resposta. Defaults to 15000.
        
        Returns:
            Dict[str, Any]: Resultado com contexto RAG aplicado.
        
        Raises:
            RuntimeError: Se o sistema RAG estiver indisponível.
            ValueError: Se a consulta RAG falhar.
        
        Example:
            >>> resultado = provider.executar_prompt_com_rag(
            ...     tipo_tarefa="policy_compliance",
            ...     prompt_principal="class UserService {}",
            ...     usar_rag=True
            ... )
        """
        pass

class ILLMProviderWithModelSelection(ILLMProvider):
    """
    Interface estendida para provedores que suportam seleção dinâmica de modelo.
    
    Esta interface permite que implementações ofereçam múltiplos modelos
    (ex: GPT-3.5, GPT-4, Claude) e permitam seleção específica baseada
    na complexidade da tarefa ou preferências do usuário.
    
    Example:
        >>> provider = MultiModelProvider()
        >>> resultado = provider.executar_prompt_com_modelo(
        ...     tipo_tarefa="complex_refactoring",
        ...     prompt_principal="legacy_code.py",
        ...     model_name="gpt-4-turbo"
        ... )
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
        
        Permite escolha dinâmica do modelo mais adequado para a tarefa,
        considerando fatores como complexidade, custo e velocidade de resposta.
        
        Args:
            tipo_tarefa (str): Tipo de análise a ser realizada.
            prompt_principal (str): Conteúdo principal para análise.
            instrucoes_extras (str, optional): Instruções adicionais. Defaults to "".
            model_name (Optional[str], optional): Nome específico do modelo. Defaults to None.
            max_token_out (int, optional): Limite de tokens na resposta. Defaults to 15000.
        
        Returns:
            Dict[str, Any]: Resultado processado pelo modelo especificado.
        
        Raises:
            ValueError: Se model_name não for suportado.
            RuntimeError: Se o modelo especificado estiver indisponível.
        
        Example:
            >>> resultado = provider.executar_prompt_com_modelo(
            ...     tipo_tarefa="architecture_review",
            ...     prompt_principal="system_design.json",
            ...     model_name="claude-3-opus"
            ... )
        """
        pass

class ILLMProviderComplete(ILLMProviderWithRAG, ILLMProviderWithModelSelection):
    """
    Interface completa que combina todas as funcionalidades de LLM.
    
    Esta interface é para provedores que suportam todas as features:
    execução básica, RAG e seleção de modelo. Implementações desta interface
    oferecem máxima flexibilidade e funcionalidade.
    
    Example:
        >>> provider = CompleteLLMProvider()
        >>> resultado = provider.executar_prompt(
        ...     tipo_tarefa="full_analysis",
        ...     prompt_principal="complex_system.json",
        ...     usar_rag=True,
        ...     model_name="gpt-4-turbo"
        ... )
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
        
        Este método unifica todas as capacidades do provedor, permitindo
        uso simultâneo de RAG, seleção de modelo e configurações avançadas
        em uma única chamada.
        
        Args:
            tipo_tarefa (str): Tipo de análise a ser realizada.
            prompt_principal (str): Conteúdo principal para análise.
            instrucoes_extras (str, optional): Instruções adicionais. Defaults to "".
            usar_rag (bool, optional): Se deve usar RAG. Defaults to False.
            model_name (Optional[str], optional): Modelo específico. Defaults to None.
            max_token_out (int, optional): Limite de tokens. Defaults to 15000.
        
        Returns:
            Dict[str, Any]: Resultado completo com todas as funcionalidades aplicadas.
        
        Raises:
            ValueError: Se parâmetros forem inválidos.
            RuntimeError: Se houver falha na execução.
        
        Example:
            >>> resultado = provider.executar_prompt(
            ...     tipo_tarefa="enterprise_audit",
            ...     prompt_principal="enterprise_codebase.json",
            ...     instrucoes_extras="Aplicar políticas corporativas",
            ...     usar_rag=True,
            ...     model_name="claude-3-opus",
            ...     max_token_out=20000
            ... )
        """
        pass