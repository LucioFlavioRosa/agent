import json
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteProcessador:
    """
    Agente especializado em processar dados estruturados (JSON) através de LLM.
    
    Este agente é projetado para receber dados estruturados de etapas anteriores
    em um workflow e processá-los usando um provedor de LLM injetado. É ideal
    para transformações de dados, análises de estruturas JSON e processamento
    de informações já organizadas.
    
    Attributes:
        llm_provider (ILLMProvider): Provedor de LLM injetado para processamento.
    
    Example:
        >>> llm_provider = OpenAILLMProvider()
        >>> agente = AgenteProcessador(llm_provider)
        >>> resultado = agente.main(
        ...     tipo_analise="refatoracao",
        ...     codigo={"instrucoes": "Refatorar código"},
        ...     instrucoes_extras="Aplicar padrões SOLID"
        ... )
    """
    
    def __init__(self, llm_provider: ILLMProvider):
        """
        Inicializa o agente com um provedor de LLM.
        
        Args:
            llm_provider (ILLMProvider): Provedor de LLM para processamento de dados.
        
        Raises:
            TypeError: Se llm_provider não implementar ILLMProvider.
        """
        self.llm_provider = llm_provider

    def main(
        self,
        tipo_analise: str,
        codigo: Dict[str, Any],
        repositorio: Optional[str] = None, # Será ignorado
        nome_branch: Optional[str] = None, # Será ignorado
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """
        Processa dados estruturados através do LLM e retorna o resultado.
        
        Este método serializa o dicionário de entrada em JSON e o envia para
        o provedor de LLM para processamento. É a função principal do agente
        e deve ser usada para todas as operações de processamento.
        
        Args:
            tipo_analise (str): Tipo de análise a ser realizada (ex: "refatoracao", "agrupamento").
            codigo (Dict[str, Any]): Dados estruturados para processamento.
            repositorio (Optional[str], optional): Nome do repositório (ignorado neste agente).
            nome_branch (Optional[str], optional): Nome da branch (ignorado neste agente).
            instrucoes_extras (str, optional): Instruções adicionais para o LLM. Defaults to "".
            usar_rag (bool, optional): Se deve usar RAG para contexto adicional. Defaults to False.
            model_name (Optional[str], optional): Nome específico do modelo LLM. Defaults to None.
            max_token_out (int, optional): Máximo de tokens na resposta. Defaults to 15000.
        
        Returns:
            Dict[str, Any]: Resultado estruturado contendo:
                - resultado (Dict): Contém a chave "reposta_final" com a resposta do LLM.
        
        Raises:
            ValueError: Se tipo_analise estiver vazio ou codigo não for um dicionário válido.
            RuntimeError: Se houver falha na comunicação com o provedor LLM.
            json.JSONEncodeError: Se os dados de entrada não puderem ser serializados.
        
        Example:
            >>> resultado = agente.main(
            ...     tipo_analise="refatoracao",
            ...     codigo={"classes": ["UserService", "OrderService"]},
            ...     instrucoes_extras="Aplicar padrão Repository"
            ... )
            >>> print(resultado["resultado"]["reposta_final"])
        """
        # Serializa o dicionário de entrada para JSON formatado
        codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False)

        # Executa o processamento através do provedor LLM
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        # Retorna o resultado em formato padronizado
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }