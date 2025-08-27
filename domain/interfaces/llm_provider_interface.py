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
    
    Contrato de Implementação:
    - Implementações devem garantir thread-safety se usadas concorrentemente
    - Respostas devem ser estruturadas consistentemente
    - Erros de rede/API devem ser encapsulados em RuntimeError
    - Validação de parâmetros deve gerar ValueError
    
    Example:
        >>> class MyLLMProvider(ILLMProvider):
        ...     def executar_prompt(self, tipo_tarefa, prompt_principal, **kwargs):
        ...         # Implementação específica
        ...         return {"reposta_final": "resultado", "tokens_entrada": 100}
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
        
        Este método define o contrato principal para execução de prompts,
        garantindo interface consistente entre diferentes provedores de LLM.
        
        Contrato de Implementação:
        - DEVE validar tipo_tarefa contra prompts disponíveis
        - DEVE limitar tokens de saída conforme max_token_out
        - DEVE incluir contexto RAG quando usar_rag=True
        - DEVE usar model_name específico quando fornecido
        - DEVE retornar estrutura padronizada de resposta
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa a ser executada. Exemplos:
                'refatoracao', 'analise', 'implementacao', 'revisao'.
                Deve corresponder a um arquivo de prompt disponível
            prompt_principal (str): Conteúdo principal do prompt, geralmente
                o código a ser analisado ou dados estruturados em JSON
            instrucoes_extras (str, optional): Instruções adicionais do usuário
                que complementam ou modificam o comportamento padrão. Defaults to ""
            usar_rag (bool, optional): Se deve usar Retrieval-Augmented Generation
                para enriquecer contexto com políticas/documentação. Defaults to False
            model_name (Optional[str], optional): Nome específico do modelo a usar.
                Se None, implementação deve usar modelo padrão. Defaults to None
            max_token_out (int, optional): Máximo de tokens na resposta.
                Implementação deve respeitar este limite. Defaults to 15000
        
        Returns:
            Dict[str, Any]: Dicionário com estrutura padronizada contendo:
                - reposta_final (str): Resposta principal do LLM
                - tokens_entrada (int): Número de tokens consumidos na entrada
                - tokens_saida (int): Número de tokens gerados na saída
                
                Estrutura mínima esperada:
                {
                    "reposta_final": "<resposta_do_llm>",
                    "tokens_entrada": <int>,
                    "tokens_saida": <int>
                }
        
        Raises:
            ValueError: Se tipo_tarefa não for suportado, parâmetros inválidos,
                ou prompt_principal estiver vazio
            RuntimeError: Se houver falha na comunicação com o LLM,
                problemas de autenticação, ou erros de rede
            TimeoutError: Se a requisição exceder o tempo limite configurado
                (implementações devem definir timeout apropriado)
        
        Note:
            - Implementações devem fazer log de erros para debugging
            - Context RAG deve ser integrado ao prompt quando usar_rag=True
            - Validação de entrada deve ser feita antes da chamada ao LLM
        """
        pass

class ILLMProviderWithRAG(ILLMProvider):
    """
    Interface estendida para provedores que suportam RAG (Retrieval-Augmented Generation).
    
    Esta interface segrega funcionalidades específicas de RAG, permitindo que
    implementações que não suportam RAG não precisem implementar métodos desnecessários.
    Segue o princípio da segregação de interfaces (ISP) do SOLID.
    
    Contrato RAG:
    - Implementações devem integrar sistema de recuperação de contexto
    - Contexto recuperado deve ser relevante ao tipo_tarefa
    - Falhas de RAG não devem impedir execução básica do prompt
    
    Example:
        >>> class RAGEnabledProvider(ILLMProviderWithRAG):
        ...     def __init__(self, rag_retriever):
        ...         self.rag_retriever = rag_retriever
        ...     def executar_prompt_com_rag(self, tipo_tarefa, prompt_principal, **kwargs):
        ...         context = self.rag_retriever.buscar_politicas(tipo_tarefa)
        ...         # Integra contexto ao prompt
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
        
        Este método especializa a execução de prompts com integração
        de Retrieval-Augmented Generation, enriquecendo o contexto
        com informações relevantes recuperadas de bases de conhecimento.
        
        Contrato RAG Específico:
        - DEVE recuperar contexto relevante quando usar_rag=True
        - DEVE integrar contexto de forma coerente ao prompt
        - DEVE degradar graciosamente se RAG falhar
        - DEVE logar tentativas e resultados de recuperação RAG
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa que determina o contexto
                RAG a ser recuperado (ex: 'refatoracao' → políticas de refatoração)
            prompt_principal (str): Conteúdo principal do prompt antes da
                integração do contexto RAG
            instrucoes_extras (str, optional): Instruções adicionais que podem
                influenciar a recuperação RAG. Defaults to ""
            usar_rag (bool, optional): Flag para ativar/desativar RAG.
                Quando False, comporta-se como executar_prompt básico. Defaults to False
            max_token_out (int, optional): Máximo de tokens na resposta,
                considerando o contexto RAG adicional. Defaults to 15000
        
        Returns:
            Dict[str, Any]: Resposta estruturada com contexto RAG incorporado.
                Mesma estrutura de ILLMProvider.executar_prompt, mas pode incluir:
                - rag_context_used (bool): Se contexto RAG foi aplicado
                - rag_sources (List[str]): Fontes do contexto recuperado
        
        Raises:
            ValueError: Se não conseguir recuperar contexto RAG relevante
                quando usar_rag=True, ou parâmetros inválidos
            RuntimeError: Se houver falha na comunicação com LLM ou sistema RAG
        
        Note:
            - Contexto RAG deve ser integrado de forma que não quebre o prompt
            - Implementações devem ter fallback se RAG não estiver disponível
            - Logging de RAG deve incluir fontes e relevância do contexto
        """
        pass

class ILLMProviderWithModelSelection(ILLMProvider):
    """
    Interface estendida para provedores que suportam seleção específica de modelo.
    
    Esta interface segrega funcionalidades de seleção de modelo, permitindo
    flexibilidade na escolha de diferentes modelos para diferentes tarefas.
    Útil para provedores que oferecem múltiplos modelos com características distintas.
    
    Contrato de Seleção de Modelo:
    - Implementações devem validar disponibilidade do modelo solicitado
    - Devem ter modelo padrão como fallback
    - Devem documentar modelos suportados
    
    Example:
        >>> class MultiModelProvider(ILLMProviderWithModelSelection):
        ...     SUPPORTED_MODELS = ["gpt-4", "gpt-3.5-turbo", "claude-3"]
        ...     def executar_prompt_com_modelo(self, tipo_tarefa, prompt_principal, model_name="gpt-4", **kwargs):
        ...         if model_name not in self.SUPPORTED_MODELS:
        ...             raise ValueError(f"Modelo {model_name} não suportado")
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
        
        Este método permite controle granular sobre qual modelo específico
        será usado para a tarefa, possibilitando otimizações baseadas no
        tipo de análise ou requisitos de qualidade/velocidade.
        
        Contrato de Seleção de Modelo:
        - DEVE validar se model_name é suportado pelo provedor
        - DEVE usar modelo padrão se model_name for None
        - DEVE documentar modelos disponíveis e suas características
        - DEVE ajustar parâmetros conforme capacidades do modelo
        
        Args:
            tipo_tarefa (str): Tipo da análise que pode influenciar a escolha
                do modelo mais adequado
            prompt_principal (str): Conteúdo principal do prompt
            instrucoes_extras (str, optional): Instruções adicionais.
                Defaults to ""
            model_name (Optional[str], optional): Nome específico do modelo.
                Exemplos: "gpt-4", "gpt-3.5-turbo", "claude-3-opus".
                Se None, usa modelo padrão da implementação. Defaults to None
            max_token_out (int, optional): Máximo de tokens na resposta,
                ajustado conforme limites do modelo específico. Defaults to 15000
        
        Returns:
            Dict[str, Any]: Resposta estruturada do modelo especificado.
                Pode incluir informações adicionais sobre o modelo usado:
                - model_used (str): Nome do modelo efetivamente usado
                - model_version (str): Versão específica do modelo
        
        Raises:
            ValueError: Se model_name não for suportado pelo provedor
                ou parâmetros incompatíveis com o modelo
            RuntimeError: Se houver falha na comunicação com o modelo específico
        
        Note:
            - Implementações devem documentar modelos suportados
            - Diferentes modelos podem ter limites de token distintos
            - Custo e velocidade podem variar entre modelos
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
    
    Contrato Completo:
    - Deve implementar todos os métodos das interfaces pai
    - Deve permitir combinação de RAG + seleção de modelo
    - Deve manter consistência entre diferentes métodos
    - Deve otimizar para uso combinado das funcionalidades
    
    Example:
        >>> class CompleteProvider(ILLMProviderComplete):
        ...     def executar_prompt(self, tipo_tarefa, prompt_principal, usar_rag=False, model_name=None, **kwargs):
        ...         # Combina RAG e seleção de modelo conforme parâmetros
        ...         if usar_rag:
        ...             context = self.get_rag_context(tipo_tarefa)
        ...         model = model_name or self.default_model
        ...         return self.call_llm(model, prompt_with_context)
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
        É o método principal para implementações completas.
        
        Contrato Unificado:
        - DEVE combinar RAG e seleção de modelo quando ambos especificados
        - DEVE otimizar contexto RAG para o modelo selecionado
        - DEVE ajustar max_token_out considerando contexto RAG adicional
        - DEVE manter consistência com métodos especializados
        
        Args:
            tipo_tarefa (str): Tipo da análise/tarefa a ser executada
            prompt_principal (str): Conteúdo principal do prompt
            instrucoes_extras (str, optional): Instruções adicionais. Defaults to ""
            usar_rag (bool, optional): Se deve usar RAG para enriquecer contexto.
                Defaults to False
            model_name (Optional[str], optional): Modelo específico a usar.
                Se None, usa padrão otimizado para o tipo_tarefa. Defaults to None
            max_token_out (int, optional): Máximo de tokens na resposta.
                Ajustado automaticamente se RAG adicionar contexto. Defaults to 15000
        
        Returns:
            Dict[str, Any]: Resposta estruturada com todas as funcionalidades aplicadas.
                Pode incluir metadados sobre RAG e modelo usado:
                - reposta_final (str): Resposta principal
                - tokens_entrada (int): Tokens de entrada (incluindo RAG)
                - tokens_saida (int): Tokens de saída
                - rag_used (bool): Se RAG foi aplicado
                - model_used (str): Modelo efetivamente usado
                - rag_sources (List[str]): Fontes RAG quando aplicável
        
        Raises:
            ValueError: Se parâmetros forem inválidos ou incompatíveis entre si
            RuntimeError: Se houver falha em qualquer componente (LLM, RAG, etc.)
            TimeoutError: Se a requisição exceder o tempo limite
        
        Note:
            - Este método deve ser a implementação mais robusta e completa
            - Deve otimizar automaticamente parâmetros para melhor resultado
            - Deve fazer fallback gracioso se alguma funcionalidade falhar
        """
        pass