# Arquivo: tools/github_reader.py (VERSÃO FINAL E CORRIGIDA)

import time
import yaml
import os
from github import GithubException, GitTreeElement, UnknownObjectException
from tools.github_connector import GitHubConnector 
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
import base64
from typing import Dict, Optional, List

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
    - Suporte a leitura filtrada por lista específica de arquivos
    - Tratamento robusto de erros de API e arquivos corrompidos
    - Suporte a diferentes tipos de análise configuráveis
    - Decodificação automática de conteúdo base64
    - Extensibilidade para múltiplos provedores de repositório
    
    Attributes:
        _mapeamento_tipo_extensoes (Dict[str, List[str]]): Mapeamento de tipos de análise
            para extensões de arquivo relevantes, carregado de workflows.yaml
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    
    Example:
        >>> # Uso com GitHub (padrão)
        >>> github_provider = GitHubRepositoryProvider()
        >>> reader = GitHubRepositoryReader(repository_provider=github_provider)
        >>> 
        >>> # Leitura completa (comportamento original)
        >>> codigo = reader.read_repository(
        ...     nome_repo="org/projeto",
        ...     tipo_analise="refatoracao",
        ...     nome_branch="main"
        ... )
        >>> 
        >>> # Leitura filtrada por arquivos específicos
        >>> codigo_filtrado = reader.read_repository(
        ...     nome_repo="org/projeto",
        ...     tipo_analise="refatoracao",
        ...     nome_branch="main",
        ...     arquivos_especificos=["src/main.py", "config/settings.py"]
        ... )
    """
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        """
        Inicializa o leitor carregando configurações de workflow.
        
        Args:
            repository_provider (Optional[IRepositoryProvider]): Provedor de repositório
                a ser usado. Se None, usa GitHubRepositoryProvider como padrão para
                manter compatibilidade com código existente.
        
        Raises:
            Exception: Se houver erro ao carregar configurações de workflow
        
        Note:
            O provedor padrão é GitHub para manter compatibilidade, mas recomenda-se
            injetar explicitamente o provedor desejado para maior clareza.
        """
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
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

    def _ler_arquivos_especificos(
        self, 
        repositorio, 
        branch_a_ler: str, 
        arquivos_especificos: List[str]
    ) -> Dict[str, str]:
        """
        Lê apenas os arquivos especificados na lista, ignorando filtros de extensão.
        
        Este método implementa a lógica de leitura filtrada, buscando apenas
        os arquivos especificados pelo usuário. É mais eficiente para casos
        onde se conhece exatamente quais arquivos são necessários.
        
        Args:
            repositorio: Objeto do repositório conectado
            branch_a_ler (str): Nome da branch a ser lida
            arquivos_especificos (List[str]): Lista de caminhos de arquivos para ler
        
        Returns:
            Dict[str, str]: Dicionário com conteúdo dos arquivos encontrados
        
        Note:
            - Arquivos não encontrados geram warning, não erro fatal
            - Usa get_contents para busca direta por path
            - Decodifica automaticamente conteúdo base64
        """
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada ativado. Lendo {total_arquivos} arquivos específicos...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                # Log de progresso
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                # Busca direta do arquivo por path e branch
                file_content = repositorio.get_contents(caminho_arquivo, ref=branch_a_ler)
                
                # Decodifica conteúdo base64
                decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                arquivos_lidos[caminho_arquivo] = decoded_content
                
            except UnknownObjectException:
                print(f"  [AVISO] Arquivo '{caminho_arquivo}' não encontrado na branch '{branch_a_ler}'. Ignorando.")
            except Exception as e:
                print(f"  [AVISO] Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"Leitura filtrada concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos

    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Lê arquivos de um repositório usando estratégia otimizada ou filtrada.
        
        Este método implementa duas estratégias de leitura:
        1. Leitura completa: Usa Git Trees API para obter todos os arquivos filtrados por extensão
        2. Leitura filtrada: Busca apenas arquivos específicos listados pelo usuário
        
        A escolha da estratégia é determinada pelo parâmetro arquivos_especificos:
        - Se None ou vazio: usa leitura completa (comportamento original)
        - Se fornecido: usa leitura filtrada, ignorando filtro por extensão
        
        Args:
            nome_repo (str): Nome do repositório no formato 'org/repo' ou 'user/repo'
            tipo_analise (str): Tipo de análise que determina quais extensões
                de arquivo serão incluídas (usado apenas na leitura completa)
            nome_branch (str, optional): Nome da branch a ser lida. Se None,
                usa a branch padrão do repositório. Defaults to None
            arquivos_especificos (Optional[List[str]], optional): Lista de caminhos
                específicos de arquivos para ler. Se fornecido, ignora filtro por
                extensão e lê apenas os arquivos listados. Defaults to None
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para conteúdo.
                Formato: {"src/main.py": "conteúdo do arquivo", ...}
                Arquivos binários ou corrompidos são automaticamente ignorados
        
        Raises:
            ValueError: Se tipo_analise não for encontrado em workflows.yaml
                ou se branch especificada não existir
            GithubException: Se houver erro de comunicação com API do provedor
            Exception: Outros erros inesperados durante a leitura
        
        Note:
            - Modo filtrado: busca apenas arquivos listados, ignora extensões
            - Modo completo: usa Git Trees API para performance otimizada
            - Arquivos não encontrados no modo filtrado geram warning, não erro
            - Funciona com qualquer provedor que implemente IRepositoryProvider
        
        Example:
            >>> # Leitura completa (comportamento original)
            >>> codigo = reader.read_repository(
            ...     nome_repo="org/projeto",
            ...     tipo_analise="refatoracao",
            ...     nome_branch="main"
            ... )
            >>> 
            >>> # Leitura filtrada por arquivos específicos
            >>> codigo_filtrado = reader.read_repository(
            ...     nome_repo="org/projeto",
            ...     tipo_analise="refatoracao",
            ...     nome_branch="main",
            ...     arquivos_especificos=["src/main.py", "config/settings.py"]
            ... )
        """
        provider_name = type(self.repository_provider).__name__
        print(f"Iniciando leitura do repositório: {nome_repo} via {provider_name}")

        # Estabelece conexão com o repositório via GitHubConnector com provedor injetado
        connector = GitHubConnector(repository_provider=self.repository_provider)
        repositorio = connector.connection(repositorio=nome_repo)

        # Determina a branch a ser lida (padrão ou especificada)
        if nome_branch is None:
            branch_a_ler = repositorio.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        # DECISÃO DE ESTRATÉGIA: Leitura filtrada vs completa
        if arquivos_especificos and len(arquivos_especificos) > 0:
            # ESTRATÉGIA 1: Leitura filtrada por lista específica
            print(f"Modo de leitura filtrada ativado para {len(arquivos_especificos)} arquivos específicos.")
            return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        
        else:
            # ESTRATÉGIA 2: Leitura completa otimizada (comportamento original)
            print("Modo de leitura completa ativado (filtro por extensão).")
            return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise)
    
    def _ler_arquivos_especificos(
        self, 
        repositorio, 
        branch_a_ler: str, 
        arquivos_especificos: List[str]
    ) -> Dict[str, str]:
        """
        Lê apenas os arquivos especificados na lista, ignorando filtros de extensão.
        
        Este método implementa a lógica de leitura filtrada, buscando apenas
        os arquivos especificados pelo usuário. É mais eficiente para casos
        onde se conhece exatamente quais arquivos são necessários.
        
        Args:
            repositorio: Objeto do repositório conectado
            branch_a_ler (str): Nome da branch a ser lida
            arquivos_especificos (List[str]): Lista de caminhos de arquivos para ler
        
        Returns:
            Dict[str, str]: Dicionário com conteúdo dos arquivos encontrados
        
        Note:
            - Arquivos não encontrados geram warning, não erro fatal
            - Usa get_contents para busca direta por path
            - Decodifica automaticamente conteúdo base64
        """
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Iniciando leitura filtrada de {total_arquivos} arquivos específicos...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                # Log de progresso
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                # Busca direta do arquivo por path e branch
                file_content = repositorio.get_contents(caminho_arquivo, ref=branch_a_ler)
                
                # Decodifica conteúdo base64
                decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                arquivos_lidos[caminho_arquivo] = decoded_content
                
            except UnknownObjectException:
                print(f"  [AVISO] Arquivo '{caminho_arquivo}' não encontrado na branch '{branch_a_ler}'. Ignorando.")
            except Exception as e:
                print(f"  [AVISO] Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"Leitura filtrada concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos
    
    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str) -> Dict[str, str]:
        """
        Implementa a lógica original de leitura completa com filtro por extensão.
        
        Este método mantém o comportamento original da classe, usando Git Trees API
        para leitura otimizada de todos os arquivos que correspondem às extensões
        configuradas para o tipo de análise.
        
        Args:
            repositorio: Objeto do repositório conectado
            branch_a_ler (str): Nome da branch a ser lida
            tipo_analise (str): Tipo de análise para filtro por extensão
        
        Returns:
            Dict[str, str]: Dicionário com conteúdo de todos os arquivos filtrados
        
        Note:
            - Mantém exatamente o comportamento original da classe
            - Usa Git Trees API para performance otimizada
            - Filtra por extensões baseadas em workflows.yaml
        """
        # Obtém extensões relevantes para o tipo de análise
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
        
        print(f"\nLeitura completa concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo