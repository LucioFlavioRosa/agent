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
    Leitor de repositórios GitHub com suporte a leitura filtrada de arquivos específicos.
    
    Esta classe implementa a interface IRepositoryReader e fornece funcionalidades
    para leitura completa (por extensão) ou filtrada (arquivos específicos) de repositórios.
    
    Características principais:
    - Leitura completa baseada em filtros de extensão por tipo de análise
    - Leitura filtrada de arquivos específicos quando solicitado
    - Suporte a múltiplos provedores de repositório via injeção de dependência
    - Tratamento robusto de erros e arquivos não encontrados
    - Logging detalhado para debugging
    
    Attributes:
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
        _mapeamento_tipo_extensoes (Dict): Mapeamento de tipos de análise para extensões
    """
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        """
        Inicializa o leitor com provedor de repositório opcional.
        
        Args:
            repository_provider (Optional[IRepositoryProvider], optional): Provedor
                de repositório a ser usado. Se None, usa GitHubRepositoryProvider
                como padrão. Defaults to None
        """
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()

    def _carregar_config_workflows(self):
        """
        Carrega configuração de workflows e cria mapeamento de tipos para extensões.
        
        Returns:
            Dict: Mapeamento de tipos de análise (lowercase) para listas de extensões
        
        Raises:
            Exception: Se houver falha ao carregar o arquivo workflows.yaml
        """
        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '..'))
            yaml_path = os.path.join(project_root, 'workflows.yaml')
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            mapeamento_expandido = {}
            for workflow_name, data in config.items():
                extensions = data.get('extensions', [])
                if not extensions:
                    continue
                
                mapeamento_expandido[workflow_name.lower()] = extensions
                
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
        Lê uma lista específica de arquivos do repositório.
        
        Este método implementa a leitura filtrada, processando apenas os arquivos
        listados em arquivos_especificos. Arquivos não encontrados são tratados
        com warning, não erro fatal.
        
        Args:
            repositorio: Objeto repositório do provedor
            branch_a_ler (str): Nome da branch a ser lida
            arquivos_especificos (List[str]): Lista de caminhos de arquivos para ler
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos para conteúdo dos arquivos
                encontrados e lidos com sucesso
        
        Note:
            - Arquivos não encontrados geram warning, não erro fatal
            - Falhas de leitura individual são tratadas graciosamente
            - Progresso é logado a cada arquivo processado
        """
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada ativado. Lendo {total_arquivos} arquivos específicos...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                # Obtém conteúdo do arquivo específico
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
        Lê os arquivos do repositório e retorna um dicionário {caminho: conteudo}.
        
        Este método implementa tanto leitura completa (filtrada por extensão)
        quanto leitura filtrada (arquivos específicos). O modo é determinado
        pela presença do parâmetro arquivos_especificos.
        
        Args:
            nome_repo (str): Nome do repositório no formato 'org/repo'
            tipo_analise (str): Tipo de análise que determina extensões relevantes
                (ignorado se arquivos_especificos for fornecido)
            nome_branch (str, optional): Nome da branch. Se None, usa branch padrão
            arquivos_especificos (Optional[List[str]], optional): Lista de caminhos
                específicos de arquivos para ler. Se fornecido, ignora filtro por
                extensão e lê apenas os arquivos listados. Defaults to None
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos de arquivo para conteúdo
        
        Note:
            - Quando arquivos_especificos é fornecido, o filtro por extensão é ignorado
            - Arquivos não encontrados são tratados com warning, não erro fatal
            - Modo padrão (arquivos_especificos=None) mantém comportamento original
        """
        provider_name = type(self.repository_provider).__name__
        print(f"Iniciando leitura do repositório: {nome_repo} via {provider_name}")

        connector = GitHubConnector(repository_provider=self.repository_provider)
        repositorio = connector.connection(repositorio=nome_repo)

        if nome_branch is None:
            branch_a_ler = repositorio.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        # Determina modo de leitura baseado na presença de arquivos_especificos
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada ativado para {len(arquivos_especificos)} arquivos específicos.")
            return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa ativado (filtro por extensão).")
            return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise)
    
    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str) -> Dict[str, str]:
        """
        Implementa leitura completa do repositório filtrada por extensões.
        
        Este método mantém o comportamento original de leitura completa,
        filtrando arquivos baseado nas extensões definidas para o tipo de análise.
        
        Args:
            repositorio: Objeto repositório do provedor
            branch_a_ler (str): Nome da branch a ser lida
            tipo_analise (str): Tipo de análise para determinar extensões relevantes
        
        Returns:
            Dict[str, str]: Dicionário mapeando caminhos para conteúdo dos arquivos
        
        Raises:
            ValueError: Se tipo de análise não for encontrado ou não tiver extensões
            GithubException: Se houver falha na comunicação com a API
        """
        extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}'...")
            
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")

            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            print(f"Árvore obtida. {len(tree_elements)} itens totais encontrados.")

            if tree_response.truncated:
                print(f"AVISO: A lista de arquivos do repositório '{nome_repo}' foi truncada pela API.")

            # Filtra arquivos por extensão
            arquivos_para_ler = [
                element for element in tree_elements
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            # Lê conteúdo de cada arquivo filtrado
            for i, element in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({element.path})")
                
                try:
                    blob_content = repositorio.get_git_blob(element.sha).content
                    
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                    
                except Exception as e:
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{element.path}'. Pulando. Erro: {e}")

        except GithubException as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API: {e}")
            raise
        
        print(f"\nLeitura completa concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo