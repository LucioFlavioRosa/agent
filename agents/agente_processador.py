import json
from typing import Optional, Dict, Any

from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteProcessador:
    """
    Agente especializado no processamento de dados estruturados (JSON) em workflows de IA.
    
    Este agente é responsável por receber dados JSON de etapas anteriores em um workflow
    e processá-los através de um provedor de LLM, mantendo o foco na transformação
    de dados estruturados sem interação direta com repositórios.
    
    Características principais:
    - Processa dados JSON já estruturados
    - Ignora parâmetros de repositório (repositorio, nome_branch)
    - Foca na transformação de dados através de IA
    - Mantém interface consistente com outros agentes do sistema
    
    Attributes:
        llm_provider (ILLMProvider): Provedor de LLM injetado para processamento
    
    Example:
        >>> from tools.requisicao_openai import OpenAILLMProvider
        >>> llm = OpenAILLMProvider()
        >>> agente = AgenteProcessador(llm)
        >>> resultado = agente.main(
        ...     tipo_analise="refatoracao",
        ...     codigo={"instrucoes": "Refatorar classe User"},
        ...     instrucoes_extras="Aplicar padrões SOLID"
        ... )
    """
    
    def __init__(self, llm_provider: ILLMProvider):
        """
        Inicializa o agente com um provedor de LLM.
        
        Args:
            llm_provider (ILLMProvider): Implementação de provedor de LLM para
                processamento de prompts e geração de respostas
        
        Raises:
            TypeError: Se llm_provider não implementar ILLMProvider
        """
        self.llm_provider = llm_provider

    def main(
        self,
        tipo_analise: str,
        codigo: Dict[str, Any],
        repositorio: Optional[str] = None,  # Será ignorado
        nome_branch: Optional[str] = None,  # Será ignorado
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """
        Processa dados estruturados através do provedor de LLM configurado.
        
        Este método é a função principal do agente, responsável por:
        1. Serializar os dados JSON de entrada
        2. Enviar para o provedor de LLM com as configurações especificadas
        3. Retornar o resultado estruturado
        
        Args:
            tipo_analise (str): Tipo de análise a ser executada (ex: 'refatoracao', 
                'implementacao', 'revisao'). Deve corresponder a um prompt disponível
            codigo (Dict[str, Any]): Dados estruturados para processamento. Geralmente
                contém resultados de etapas anteriores do workflow
            repositorio (Optional[str], optional): Parâmetro ignorado. Mantido para
                compatibilidade de interface. Defaults to None
            nome_branch (Optional[str], optional): Parâmetro ignorado. Mantido para
                compatibilidade de interface. Defaults to None
            instrucoes_extras (str, optional): Instruções adicionais do usuário que
                serão incluídas no prompt. Defaults to ""
            usar_rag (bool, optional): Se deve utilizar Retrieval-Augmented Generation
                para enriquecer o contexto. Defaults to False
            model_name (Optional[str], optional): Nome específico do modelo de LLM.
                Se None, usa o modelo padrão do provedor. Defaults to None
            max_token_out (int, optional): Limite máximo de tokens na resposta.
                Defaults to 15000
        
        Returns:
            Dict[str, Any]: Dicionário estruturado contendo:
                - resultado (Dict): Contém a chave 'reposta_final' com a resposta do LLM
                - Estrutura: {"resultado": {"reposta_final": <resposta_do_llm>}}
        
        Raises:
            ValueError: Se tipo_analise for inválido ou codigo estiver vazio
            RuntimeError: Se houver falha na comunicação com o provedor de LLM
            json.JSONEncodeError: Se os dados de entrada não forem serializáveis
        
        Note:
            - Os parâmetros repositorio e nome_branch são ignorados intencionalmente
            - O código de entrada é serializado em JSON com formatação legível
            - Instruções extras são passadas diretamente ao provedor de LLM
        """
        # Serializa os dados de entrada em formato JSON legível para o LLM
        codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False)

        # Delega o processamento para o provedor de LLM injetado
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        # Retorna resultado em formato padronizado esperado pelo sistema
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }