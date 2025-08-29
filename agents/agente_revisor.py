import json
from typing import Optional, Dict, Any
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from tools.repository_provider_factory import get_repository_provider
from tools.github_reader import GitHubRepositoryReader

class AgenteRevisor:
    """
    Orquestrador especializado em análise de código via IA com integração a repositórios.
    
    Este agente é responsável por coordenar a leitura de repositórios GitHub, GitLab
    e Azure DevOps e iniciar análises de código através de provedores de LLM. Sua responsabilidade
    única é orquestrar o fluxo: repositório → detecção de provider → leitura → análise → resultado.
    
    Características principais:
    - Detecção automática do tipo de repositório (GitHub, GitLab, Azure DevOps)
    - Integração com repositórios através de interface abstrata
    - Processamento de código via provedores de LLM
    - Tratamento robusto de erros de leitura de repositório
    - Suporte a diferentes tipos de análise configuráveis
    
    Attributes:
        repository_reader (IRepositoryReader): Interface para leitura de repositórios
        llm_provider (ILLMProvider): Provedor de LLM para análise do código
    
    Example:
        >>> from tools.requisicao_openai import OpenAILLMProvider
        >>> llm = OpenAILLMProvider()
        >>> agente = AgenteRevisor(llm_provider=llm)
        >>> resultado = agente.main(
        ...     tipo_analise="refatoracao",
        ...     repositorio="org/projeto",  # GitHub detectado automaticamente
        ...     nome_branch="main"
        ... )
        >>> 
        >>> # Também funciona com GitLab e Azure DevOps
        >>> resultado = agente.main(
        ...     tipo_analise="refatoracao",
        ...     repositorio="gitlab-org/gitlab",  # GitLab detectado automaticamente
        ...     nome_branch="main"
        ... )
    """
    
    def __init__(
        self,
        repository_reader: Optional[IRepositoryReader] = None,
        llm_provider: Optional[ILLMProvider] = None
    ):
        """
        Inicializa o agente com as dependências necessárias.
        
        Args:
            repository_reader (Optional[IRepositoryReader]): Implementação de leitor de repositório.
                Se None, usa GitHubRepositoryReader com detecção automática de provider
            llm_provider (Optional[ILLMProvider]): Implementação de provedor de LLM que será
                usado para análise do código obtido. Deve ser fornecido para funcionamento
        
        Raises:
            TypeError: Se as dependências não implementarem as interfaces esperadas
        
        Note:
            O repository_reader padrão (GitHubRepositoryReader) agora suporta detecção
            automática de provedores, funcionando transparentemente com GitHub, GitLab
            e Azure DevOps baseado no formato do nome do repositório.
        """
        self.repository_reader = repository_reader or GitHubRepositoryReader()
        self.llm_provider = llm_provider

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str
    ) -> Dict[str, str]:
        """
        Obtém código-fonte de um repositório usando detecção automática de provider.
        
        Este método privado encapsula a lógica de leitura de repositório com
        detecção automática do tipo de provider (GitHub, GitLab, Azure DevOps),
        fornecendo tratamento de erro consistente e logging para debugging.
        
        Args:
            repositorio (str): Nome do repositório. Formatos suportados:
                - GitHub: 'org/repo' ou 'user/repo'
                - GitLab: 'grupo/projeto' (detectado por heurísticas)
                - Azure DevOps: 'organization/project/repository'
            nome_branch (Optional[str]): Nome da branch a ser lida. Se None,
                usa a branch padrão do repositório
            tipo_analise (str): Tipo de análise que determina quais arquivos
                serão filtrados durante a leitura
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para seu conteúdo.
                Formato: {"caminho/arquivo.py": "conteúdo do arquivo"}
        
        Raises:
            RuntimeError: Se houver falha na leitura do repositório, encapsulando
                a exceção original para contexto adicional
            ValueError: Se o formato do repositório for inválido ou tipo_analise
                não for reconhecido
        
        Note:
            - O tipo_analise é usado pelo repository_reader para filtrar arquivos relevantes
            - Logging é feito para facilitar debugging de problemas de conectividade
            - A detecção de provider é automática baseada no nome do repositório
            - Suporta GitHub, GitLab e Azure DevOps transparentemente
        """
        try:
            print(f"Iniciando a leitura do repositório: {repositorio}, branch: {nome_branch}")
            print(f"Detecção automática de provider será aplicada baseada no formato do repositório.")
            
            # Delega a leitura para a implementação injetada
            # O GitHubRepositoryReader agora detecta automaticamente o provider correto
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                nome_branch=nome_branch
            )
            
            return codigo_para_analise
            
        except Exception as e:
            # Encapsula exceções com contexto adicional para debugging
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
        Orquestra a obtenção de código de repositório e análise via IA com suporte multi-provedor.
        
        Este é o método principal que coordena todo o fluxo do agente:
        1. Detecta automaticamente o tipo de repositório (GitHub, GitLab, Azure DevOps)
        2. Obtém código do repositório através do repository_reader
        3. Valida se código foi encontrado
        4. Serializa código em formato JSON
        5. Envia para análise via llm_provider
        6. Retorna resultado estruturado
        
        Args:
            tipo_analise (str): Tipo de análise a ser executada. Deve corresponder
                a um prompt disponível no sistema (ex: 'refatoracao', 'revisao')
            repositorio (str): Nome do repositório. Formatos aceitos:
                - GitHub: 'org/repo', 'user/repo' (formato padrão)
                - GitLab: 'grupo/projeto' (detectado por heurísticas como 'gitlab-org/gitlab')
                - Azure DevOps: 'organization/project/repository' (3 partes)
            nome_branch (Optional[str], optional): Nome da branch a ser analisada.
                Se None, usa a branch padrão. Defaults to None
            instrucoes_extras (str, optional): Instruções adicionais do usuário
                que complementam a análise. Defaults to ""
            usar_rag (bool, optional): Se deve usar Retrieval-Augmented Generation
                para enriquecer o contexto da análise. Defaults to False
            model_name (Optional[str], optional): Nome específico do modelo de LLM.
                Se None, usa o modelo padrão do provedor. Defaults to None
            max_token_out (int, optional): Limite máximo de tokens na resposta
                do LLM. Defaults to 15000
        
        Returns:
            Dict[str, Any]: Resultado estruturado da análise contendo:
                - resultado (Dict): Contém 'reposta_final' com a análise do LLM
                - Se nenhum código for encontrado, retorna estrutura vazia
                - Formato: {"resultado": {"reposta_final": <analise_do_llm>}}
        
        Raises:
            RuntimeError: Se houver falha na leitura do repositório
            ValueError: Se tipo_analise for inválido, repositorio mal formatado,
                ou formato de repositório não suportado
            Exception: Erros de comunicação com o provedor de LLM são propagados
        
        Note:
            - Detecção automática de provider baseada no formato do repositório
            - Se nenhum código for encontrado, retorna resultado vazio sem erro
            - O código é serializado em JSON com formatação legível
            - Avisos são impressos para facilitar debugging
            - Suporta GitHub, GitLab e Azure DevOps transparentemente
            - Funciona com qualquer repository_reader que implemente IRepositoryReader
        """
        # Etapa 1: Obter código do repositório com detecção automática de provider
        codigo_para_analise = self._get_code(
            repositorio=repositorio,
            nome_branch=nome_branch,
            tipo_analise=tipo_analise
        )

        # Etapa 2: Validar se código foi encontrado
        if not codigo_para_analise:
            print(f"AVISO: Nenhum código encontrado no repositório para a análise '{tipo_analise}'.")
            return {"resultado": {"reposta_final": {}}}

        # Etapa 3: Serializar código em formato JSON legível
        codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)

        # Etapa 4: Enviar para análise via provedor de LLM
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        # Etapa 5: Retornar resultado em formato padronizado
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }