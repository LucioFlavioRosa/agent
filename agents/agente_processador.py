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
    - Tratamento robusto de retornos do provedor LLM
    
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
        if not hasattr(llm_provider, 'executar_prompt'):
            raise TypeError("llm_provider deve implementar ILLMProvider com método executar_prompt")
        self.llm_provider = llm_provider

    def _validar_e_extrair_resposta(self, resultado_llm: Any) -> str:
        """
        Valida e extrai a resposta final do retorno do provedor LLM.
        
        Este método garante compatibilidade com diferentes implementações de ILLMProvider,
        tratando tanto retornos diretos (string) quanto estruturados (dict).
        
        Args:
            resultado_llm (Any): Retorno do método executar_prompt do provedor
            
        Returns:
            str: Resposta final extraída e validada
            
        Raises:
            ValueError: Se o retorno não contiver dados válidos
            TypeError: Se o retorno não for do tipo esperado
        """
        # Caso 1: Retorno direto como string
        if isinstance(resultado_llm, str):
            if not resultado_llm.strip():
                raise ValueError("Provedor LLM retornou string vazia")
            return resultado_llm.strip()
        
        # Caso 2: Retorno estruturado como dict (conforme interface ILLMProvider)
        if isinstance(resultado_llm, dict):
            # Verifica se contém a chave obrigatória 'reposta_final'
            if 'reposta_final' not in resultado_llm:
                raise ValueError(
                    "Retorno do provedor LLM não contém chave obrigatória 'reposta_final'. "
                    f"Chaves disponíveis: {list(resultado_llm.keys())}"
                )
            
            resposta_final = resultado_llm['reposta_final']
            
            # Valida se a resposta final é uma string não vazia
            if not isinstance(resposta_final, str):
                raise TypeError(
                    f"Chave 'reposta_final' deve ser string, recebido: {type(resposta_final).__name__}"
                )
            
            if not resposta_final.strip():
                raise ValueError("Chave 'reposta_final' contém string vazia")
            
            return resposta_final.strip()
        
        # Caso 3: Tipo não suportado
        raise TypeError(
            f"Retorno do provedor LLM deve ser string ou dict, recebido: {type(resultado_llm).__name__}"
        )

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
        3. Validar e extrair a resposta do provedor
        4. Retornar o resultado estruturado
        
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
            ValueError: Se tipo_analise for inválido ou codigo estiver vazio,
                ou se o provedor retornar dados inválidos
            RuntimeError: Se houver falha na comunicação com o provedor de LLM
            TypeError: Se os dados de entrada não forem serializáveis
                ou se o retorno do provedor não for do tipo esperado
        
        Note:
            - Os parâmetros repositorio e nome_branch são ignorados intencionalmente
            - O código de entrada é serializado em JSON com formatação legível
            - Instruções extras são passadas diretamente ao provedor de LLM
            - Validação robusta do retorno do provedor garante compatibilidade
        """
        # Validação de entrada
        if not tipo_analise or not isinstance(tipo_analise, str):
            raise ValueError("tipo_analise deve ser uma string não vazia")
        
        if not codigo or not isinstance(codigo, dict):
            raise ValueError("codigo deve ser um dicionário não vazio")
        
        try:
            # Serializa os dados de entrada em formato JSON legível para o LLM
            codigo_str = json.dumps(codigo, indent=2, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"Erro ao serializar dados de entrada: {e}"
            ) from e

        try:
            # Delega o processamento para o provedor de LLM injetado
            resultado_da_ia = self.llm_provider.executar_prompt(
                tipo_tarefa=tipo_analise,
                prompt_principal=codigo_str,
                instrucoes_extras=instrucoes_extras,
                usar_rag=usar_rag,
                model_name=model_name,
                max_token_out=max_token_out
            )
        except Exception as e:
            raise RuntimeError(f"Falha na comunicação com o provedor de LLM: {e}") from e

        # Valida e extrai a resposta final do provedor
        try:
            resposta_final_validada = self._validar_e_extrair_resposta(resultado_da_ia)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Retorno inválido do provedor LLM: {e}") from e

        # Retorna resultado em formato padronizado esperado pelo sistema
        return {
            "resultado": {
                "reposta_final": resposta_final_validada
            }
        }