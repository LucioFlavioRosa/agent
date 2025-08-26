import json
from typing import Optional, Dict, Any
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteRevisor:
    """
    Orquestrador de análise de código via IA para repositórios GitHub.
    
    Este agente é responsável por ler código de repositórios remotos e
    iniciar análises através de provedores de LLM. Combina a funcionalidade
    de leitura de repositório com processamento de IA para análises completas.
    
    Attributes:
        repository_reader (IRepositoryReader): Interface para leitura de repositórios.
        llm_provider (ILLMProvider): Provedor de LLM para análise do código.
    
    Example:
        >>> repo_reader = GitHubRepositoryReader()
        >>> llm_provider = OpenAILLMProvider()
        >>> agente = AgenteRevisor(repo_reader, llm_provider)
        >>> resultado = agente.main(
        ...     tipo_analise="code_review",
        ...     repositorio="org/repo",
        ...     nome_branch="main"
        ... )
    """
    
    def __init__(
        self,
        repository_reader: IRepositoryReader,
        llm_provider: ILLMProvider
    ):
        """
        Inicializa o agente com as dependências necessárias.
        
        Args:
            repository_reader (IRepositoryReader): Implementação para leitura de repositórios.
            llm_provider (ILLMProvider): Provedor de LLM para análise.
        
        Raises:
            TypeError: Se as dependências não implementarem as interfaces corretas.
        """
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str
    ) -> Dict[str, str]:
        """
        Obtém o código de um repositório usando a interface injetada.
        
        Este método privado encapsula a lógica de leitura de repositório,
        incluindo tratamento de erros e logging. Utiliza a interface
        IRepositoryReader para abstrair a implementação específica.
        
        Args:
            repositorio (str): Nome do repositório no formato 'org/repo'.
            nome_branch (Optional[str]): Nome da branch a ser lida. Se None, usa a branch padrão.
            tipo_analise (str): Tipo de análise para filtrar arquivos relevantes.
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para seu conteúdo.
                Formato: {"caminho/arquivo.py": "conteúdo do arquivo"}
        
        Raises:
            RuntimeError: Se houver falha na leitura do repositório.
            ValueError: Se o repositório não for encontrado ou estiver inacessível.
            ConnectionError: Se houver problemas de conectividade com o provedor.
        
        Example:
            >>> codigo = self._get_code("org/repo", "main", "code_review")
            >>> print(list(codigo.keys()))  # Lista os arquivos lidos
        """
        try:
            print(f"Iniciando a leitura do repositório: {repositorio}, branch: {nome_branch}")
            
            # Chama a interface de leitura de repositório
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                nome_branch=nome_branch
            )
            
            return codigo_para_analise
        except Exception as e:
            # Propaga o erro com contexto adicional
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

    def main(
        self,
        tipo_analise: str,
        repositorio: str,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000
    ) -> Dict[str, Any]:
        """
        Orquestra a obtenção do código de um repositório e a análise via IA.
        
        Este é o método principal do agente que coordena todo o fluxo:
        1. Lê o código do repositório especificado
        2. Serializa o código para formato JSON
        3. Envia para o provedor LLM para análise
        4. Retorna o resultado estruturado
        
        Args:
            tipo_analise (str): Tipo de análise a ser realizada (ex: "code_review", "security_audit").
            repositorio (str): Nome do repositório no formato 'org/repo'.
            nome_branch (Optional[str], optional): Branch a ser analisada. Defaults to None (branch padrão).
            instrucoes_extras (str, optional): Instruções adicionais para a análise. Defaults to "".
            usar_rag (bool, optional): Se deve usar RAG para contexto adicional. Defaults to False.
            model_name (Optional[str], optional): Nome específico do modelo LLM. Defaults to None.
            max_token_out (int, optional): Máximo de tokens na resposta. Defaults to 15000.
        
        Returns:
            Dict[str, Any]: Resultado estruturado contendo:
                - resultado (Dict): Contém a chave "reposta_final" com a análise do LLM.
        
        Raises:
            ValueError: Se repositorio estiver vazio ou tipo_analise for inválido.
            RuntimeError: Se houver falha na leitura do repositório ou comunicação com LLM.
            ConnectionError: Se houver problemas de conectividade.
        
        Example:
            >>> resultado = agente.main(
            ...     tipo_analise="security_audit",
            ...     repositorio="myorg/myrepo",
            ...     nome_branch="develop",
            ...     instrucoes_extras="Focar em vulnerabilidades SQL injection"
            ... )
            >>> analise = resultado["resultado"]["reposta_final"]
        """
        # Obtém o código do repositório
        codigo_para_analise = self._get_code(
            repositorio=repositorio,
            nome_branch=nome_branch,
            tipo_analise=tipo_analise
        )

        # Verifica se algum código foi encontrado
        if not codigo_para_analise:
            print(f"AVISO: Nenhum código encontrado no repositório para a análise '{tipo_analise}'.")
            return {"resultado": {"reposta_final": {}}}

        # Serializa o código para JSON formatado
        codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)

        # Executa a análise através do provedor LLM
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