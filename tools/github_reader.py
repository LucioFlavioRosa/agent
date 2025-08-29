# Arquivo: tools/github_reader.py (VERSÃO FINAL E CORRIGIDA)

import time
import yaml
import os
from github import GithubException, GitTreeElement, UnknownObjectException
from tools.github_connector import GitHubConnector 
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.repository_provider_factory import get_repository_provider
import base64
from typing import Dict, Optional

class GitHubRepositoryReader(IRepositoryReader):
    """
    Implementação otimizada e robusta que usa a API Git Trees para leitura rápida de repositórios.
    
    Esta classe implementa uma estratégia de leitura otimizada que utiliza a API Git Trees
    para obter toda a estrutura de arquivos de uma vez, em vez de fazer múltiplas chamadas
    individuais. Agora é agnóstica ao provedor de repositório específico.
    
    IMPORTANTE: Esta classe agora aceita qualquer provedor de repositório via injeção
    de dependência, permitindo uso com GitHub, GitLab, Bitbucket ou outros provedores
    que implementem IRepositoryProvider.
    
    Características principais:
    - Uso da API Git Trees para leitura em lote
    - Filtragem inteligente por extensões baseada em workflows
    - Tratamento robusto de erros de API e arquivos corrompidos
    - Suporte a diferentes tipos de análise configuráveis
    - Decodificação automática de conteúdo base64
    - Extensibilidade para múltiplos provedores de repositório
    - Detecção automática do provedor baseada no nome do repositório
    
    Attributes:
        _mapeamento_tipo_extensoes (Dict[str, List[str]]): Mapeamento de tipos de análise
            para extensões de arquivo relevantes, carregado de workflows.yaml
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    
    Example:
        >>> # Uso com detecção automática (recomendado)
        >>> reader = GitHubRepositoryReader()
        >>> codigo = reader.read_repository(
        ...     nome_repo="org/projeto",  # GitHub detectado automaticamente
        ...     tipo_analise="refatoracao"
        ... )
        >>> 
        >>> # Uso com provider explícito (para casos especiais)
        >>> gitlab_provider = GitLabRepositoryProvider()
        >>> reader = GitHubRepositoryReader(repository_provider=gitlab_provider)
    """
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        """
        Inicializa o leitor carregando configurações de workflow.
        
        Args:
            repository_provider (Optional[IRepositoryProvider]): Provedor de repositório
                a ser usado. Se None, a detecção automática será usada baseada no
                nome do repositório durante a leitura.
        
        Raises:
            Exception: Se houver erro ao carregar configurações de workflow
        
        Note:
            Quando repository_provider é None, a detecção automática é feita durante
            a chamada de read_repository usando a factory get_repository_provider.
            Isso permite máxima flexibilidade e uso transparente.
        """
        self.repository_provider = repository_provider
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

    def _get_or_detect_provider(self, nome_repo: str) -> IRepositoryProvider:
        """
        Obtém o provider de repositório, usando detecção automática se necessário.
        
        Este método implementa a lógica de detecção automática quando nenhum
        provider foi injetado no construtor. Utiliza a factory para determinar
        o tipo correto baseado no nome do repositório.
        
        Args:
            nome_repo (str): Nome do repositório no formato 'org/repo' ou equivalente
            
        Returns:
            IRepositoryProvider: Provider apropriado para o repositório
            
        Note:
            - Se repository_provider foi injetado, usa o injetado
            - Caso contrário, usa factory para detecção automática
            - Faz log da detecção para debugging
        """
        if self.repository_provider is not None:
            provider_name = type(self.repository_provider).__name__
            print(f"Usando provider injetado: {provider_name} para repositório {nome_repo}")
            return self.repository_provider
        
        print(f"Detectando provider automaticamente para repositório: {nome_repo}")
        detected_provider = get_repository_provider(nome_repo)
        provider_name = type(detected_provider).__name__
        print(f"Provider detectado: {provider_name}")
        return detected_provider

    def read_repository(self, nome_repo: str, tipo_analise: str, nome_branch: str = None) -> dict:
        """
        Lê arquivos de um repositório usando estratégia otimizada com detecção automática de provider.
        
        Este método implementa uma estratégia de leitura em duas fases:
        1. Detecção automática do provider (se não foi injetado)
        2. Obtenção da árvore completa de arquivos via Git Trees API
        3. Leitura em lote do conteúdo dos arquivos filtrados
        
        A abordagem é significativamente mais eficiente que leitura individual
        de arquivos, especialmente para repositórios grandes.
        
        Args:
            nome_repo (str): Nome do repositório no formato 'org/repo' ou 'user/repo'.
                O formato determina automaticamente o provider:
                - 'org/repo' → GitHub (padrão) ou GitLab (com heurísticas)
                - 'org/project/repo' → Azure DevOps
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
                ou se branch especificada não existir, ou formato de repo inválido
            GithubException: Se houver erro de comunicação com API do provedor
            Exception: Outros erros inesperados durante a leitura
        
        Note:
            - Usa detecção automática de provider baseada no nome do repositório
            - Usa Git Trees API para performance otimizada
            - Filtra automaticamente por extensões relevantes
            - Ignora arquivos binários e diretórios
            - Faz log de progresso para repositórios grandes
            - Funciona transparentemente com GitHub, GitLab e Azure DevOps
        """
        # ETAPA 1: Detecção automática do provider
        provider = self._get_or_detect_provider(nome_repo)
        provider_name = type(provider).__name__
        print(f"Iniciando leitura otimizada do repositório: {nome_repo} via {provider_name}")

        # ETAPA 2: Estabelece conexão com o repositório via GitHubConnector com provedor detectado
        connector = GitHubConnector(repository_provider=provider)
        repositorio = connector.connection(repositorio=nome_repo)

        # ETAPA 3: Determina a branch a ser lida (padrão ou especificada)
        if nome_branch is None:
            branch_a_ler = repositorio.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        # ETAPA 4: Obtém extensões relevantes para o tipo de análise
        extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}'...")
            
            # FASE 1: Obtenção da árvore Git completa
            # Esta é a otimização principal - uma única chamada API para toda a estrutura
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")

            # Chamada recursiva obtém toda a estrutura de arquivos de uma vez
            # recursive=True garante que subdiretórios sejam incluídos na resposta
            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            print(f"Árvore obtida. {len(tree_elements)} itens totais encontrados.")

            # Verificação de truncamento da API
            # A API pode truncar listas muito grandes (>100k itens)
            if tree_response.truncated:
                print(f"AVISO: A lista de arquivos do repositório '{nome_repo}' foi truncada pela API.")

            # FASE 2: Filtragem inteligente por extensão
            # Seleciona apenas arquivos (type='blob') com extensões relevantes
            # Exclui diretórios, symlinks e outros objetos Git
            arquivos_para_ler = [
                element for element in tree_elements
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            # FASE 3: Leitura otimizada do conteúdo
            # Usa Git Blob API para acesso direto via SHA, evitando múltiplas chamadas
            for i, element in enumerate(arquivos_para_ler):
                # Log de progresso para repositórios grandes
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({element.path})")
                
                try:
                    # Obtenção direta do blob via SHA (mais eficiente que path-based)
                    blob_content = repositorio.get_git_blob(element.sha).content
                    
                    # Decodificação do conteúdo base64 retornado pela API
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                    
                except Exception as e:
                    # Tratamento gracioso de arquivos problemáticos
                    # Arquivos binários ou corrompidos são ignorados sem interromper o processo
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{element.path}'. Pulando. Erro: {e}")

        except GithubException as e:
            # Tratamento específico de erros da API
            print(f"ERRO CRÍTICO durante a comunicação com a API: {e}")
            raise
        
        print(f"\nLeitura otimizada concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo