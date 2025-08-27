import time
import yaml
import os
from gitlab.exceptions import GitlabGetError
from tools.gitlab_connector import GitLabConnector
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
import base64
from typing import Dict, Optional, List

class GitLabRepositoryReader(IRepositoryReader):
    """
    Implementação otimizada para leitura de repositórios GitLab usando API de árvore.
    
    Esta classe implementa uma estratégia de leitura otimizada que utiliza a API
    de árvore do GitLab para obter toda a estrutura de arquivos de uma vez,
    em vez de fazer múltiplas chamadas individuais.
    
    Segue o mesmo padrão arquitetural do GitHubRepositoryReader, garantindo
    consistência na base de código e facilitando manutenção.
    
    Características principais:
    - Uso da API de árvore do GitLab para leitura em lote
    - Filtragem inteligente por extensões baseada em workflows
    - Tratamento robusto de erros de API e arquivos corrompidos
    - Suporte a diferentes tipos de análise configuráveis
    - Decodificação automática de conteúdo base64
    - Injeção de dependência para flexibilidade de provedores
    
    Attributes:
        _mapeamento_tipo_extensoes (Dict[str, List[str]]): Mapeamento de tipos de análise
            para extensões de arquivo relevantes, carregado de workflows.yaml
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    
    Example:
        >>> gitlab_provider = GitLabRepositoryProvider()
        >>> reader = GitLabRepositoryReader(repository_provider=gitlab_provider)
        >>> codigo = reader.read_repository(
        ...     nome_repo="namespace/projeto",
        ...     tipo_analise="refatoracao",
        ...     nome_branch="main"
        ... )
    """
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        """
        Inicializa o leitor carregando configurações de workflow.
        
        Args:
            repository_provider (Optional[IRepositoryProvider]): Provedor de repositório
                a ser usado. Se None, usa GitLabRepositoryProvider como padrão.
        
        Raises:
            Exception: Se houver erro ao carregar configurações de workflow
        
        Note:
            O provedor padrão é GitLab para manter consistência com a classe,
            mas recomenda-se injetar explicitamente o provedor desejado.
        """
        self.repository_provider = repository_provider or GitLabRepositoryProvider()
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()

    def _carregar_config_workflows(self):
        """
        Carrega configurações de workflow e constrói mapeamento de extensões.
        
        Este método privado lê o arquivo workflows.yaml e constrói um dicionário
        que mapeia tipos de análise para listas de extensões de arquivo relevantes.
        Isso permite que o leitor filtre apenas arquivos pertinentes para cada
        tipo de análise, otimizando performance e relevância.
        
        Returns:
            Dict[str, List[str]]: Mapeamento de tipo_analise (lowercase) para
                lista de extensões (ex: {'refatoracao': ['.py', '.java']})
        
        Raises:
            Exception: Se workflows.yaml não for encontrado ou tiver formato inválido
        
        Note:
            - Busca workflows.yaml na raiz do projeto
            - Cria mapeamentos tanto para workflow names quanto step tipo_analise
            - Converte chaves para lowercase para busca case-insensitive
        """
        try:
            # Localiza o arquivo workflows.yaml na raiz do projeto
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '..'))
            yaml_path = os.path.join(project_root, 'workflows.yaml')
            
            # Carrega e parseia o arquivo YAML
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Constrói mapeamento expandido incluindo steps internos
            mapeamento_expandido = {}
            for workflow_name, data in config.items():
                extensions = data.get('extensions', [])
                if not extensions:
                    continue
                
                # Mapeia nome do workflow principal
                mapeamento_expandido[workflow_name.lower()] = extensions
                
                # Mapeia tipo_analise de cada step individual
                for step in data.get('steps', []):
                    params = step.get('params', {})
                    tipo_analise_step = params.get('tipo_analise')
                    if tipo_analise_step:
                        mapeamento_expandido[tipo_analise_step.lower()] = extensions
            
            return mapeamento_expandido
            
        except Exception as e:
            print(f"ERRO INESPERADO ao carregar workflows: {e}")
            raise

    def read_repository(self, nome_repo: str, tipo_analise: str, nome_branch: str = None) -> dict:
        """
        Lê arquivos de um repositório GitLab usando estratégia otimizada.
        
        Este método implementa uma estratégia de leitura em duas fases:
        1. Obtenção da árvore completa de arquivos via API de árvore do GitLab
        2. Leitura em lote do conteúdo dos arquivos filtrados
        
        A abordagem é significativamente mais eficiente que leitura individual
        de arquivos, especialmente para repositórios grandes.
        
        Args:
            nome_repo (str): Nome do repositório no formato 'namespace/projeto'
            tipo_analise (str): Tipo de análise que determina quais extensões
                de arquivo serão incluídas (deve existir em workflows.yaml)
            nome_branch (str, optional): Nome da branch a ser lida. Se None,
                usa a branch padrão do repositório. Defaults to None
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para conteúdo.
                Formato: {"src/main.py": "conteúdo do arquivo", ...}
                Arquivos binários ou corrompidos são automaticamente ignorados
        
        Raises:
            ValueError: Se tipo_analise não for encontrado em workflows.yaml
                ou se branch especificada não existir
            GitlabGetError: Se houver erro de comunicação com API do GitLab
            Exception: Outros erros inesperados durante a leitura
        
        Note:
            - Usa API de árvore do GitLab para performance otimizada
            - Filtra automaticamente por extensões relevantes
            - Ignora arquivos binários e diretórios
            - Faz log de progresso para repositórios grandes
            - Funciona com qualquer provedor que implemente IRepositoryProvider
        """
        provider_name = type(self.repository_provider).__name__
        print(f"Iniciando leitura otimizada do projeto: {nome_repo} via {provider_name}")

        # Estabelece conexão com o repositório via GitLabConnector com provedor injetado
        connector = GitLabConnector(repository_provider=self.repository_provider)
        projeto = connector.connection(repositorio=nome_repo)

        # Determina a branch a ser lida (padrão ou especificada)
        if nome_branch is None:
            branch_a_ler = projeto.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        # Obtém extensões relevantes para o tipo de análise
        extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}'...")
            
            # FASE 1: Obtenção da árvore GitLab completa
            # Esta é a otimização principal - uma única chamada API para toda a estrutura
            try:
                # Obtém a árvore recursiva do projeto na branch especificada
                tree_items = projeto.repository_tree(
                    ref=branch_a_ler,
                    recursive=True,
                    all=True  # Obtém todos os itens, não apenas os primeiros 20
                )
            except GitlabGetError as e:
                if e.response_code == 404:
                    raise ValueError(f"Branch '{branch_a_ler}' não encontrada no projeto.")
                else:
                    raise ValueError(f"Erro ao acessar árvore da branch '{branch_a_ler}': {e.error_message}")

            print(f"Árvore obtida. {len(tree_items)} itens totais encontrados.")

            # FASE 2: Filtragem inteligente por extensão
            # Seleciona apenas arquivos (type='blob') com extensões relevantes
            # Exclui diretórios, symlinks e outros objetos Git
            arquivos_para_ler = [
                item for item in tree_items
                if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            # FASE 3: Leitura otimizada do conteúdo
            # Usa API de arquivo do GitLab para acesso direto
            for i, item in enumerate(arquivos_para_ler):
                # Log de progresso para repositórios grandes
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({item['path']})")
                
                try:
                    # Obtenção do conteúdo do arquivo via API do GitLab
                    file_content = projeto.files.get(
                        file_path=item['path'],
                        ref=branch_a_ler
                    )
                    
                    # Decodificação do conteúdo base64 retornado pela API
                    decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                    arquivos_do_repo[item['path']] = decoded_content
                    
                except Exception as e:
                    # Tratamento gracioso de arquivos problemáticos
                    # Arquivos binários ou corrompidos são ignorados sem interromper o processo
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{item['path']}'. Pulando. Erro: {e}")

        except GitlabGetError as e:
            # Tratamento específico de erros da API do GitLab
            print(f"ERRO CRÍTICO durante a comunicação com a API do GitLab: {e.error_message}")
            raise
        
        print(f"\nLeitura otimizada concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo