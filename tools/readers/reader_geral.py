import time
import yaml
import os
from typing import Dict, Optional, List, Union, Any
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.conectores.conexao_geral import ConexaoGeral
from .github_reader import GitHubReader
from .gitlab_reader import GitLabReader
from .azure_reader import AzureReader

class ReaderGeral(IRepositoryReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None, cache_service: Optional[Any] = None):
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()
        self.github_reader = GitHubReader(repository_provider)
        self.gitlab_reader = GitLabReader(repository_provider)
        self.azure_reader = AzureReader(repository_provider)
        self.cache_service = cache_service

    def _carregar_config_workflows(self):
        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '../..'))
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

    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str,
        repository_type: str,
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        provider_name = type(self.repository_provider).__name__
        print(f"[Reader Geral] Iniciando leitura do repositório: {nome_repo} via {provider_name}")
        print(f"[Reader Geral] Tipo de repositório explícito: {repository_type}")
        print(f"[Reader Geral] Flag retornar_lista_arquivos: {retornar_lista_arquivos}")
        conexao_geral = ConexaoGeral.create_with_defaults()
        print(f"[Reader Geral] Usando repository_type explícito: {repository_type}")
        repositorio = conexao_geral.connection(repositorio=nome_repo, repository_type=repository_type, repository_provider=self.repository_provider)
        print(f"[Reader Geral] Objeto repositório recebido: {type(repositorio)}")
        resultado = None
        cache_resultado = {}
        cache_ttl = 3600
        arquivos_para_ler = arquivos_especificos if arquivos_especificos is not None else None
        lista_arquivos_cache_key = f"repo_file_list:{repository_type}:{nome_repo}:{nome_branch}"
        lista_arquivos_do_cache = None
        if retornar_lista_arquivos and self.cache_service:
            if hasattr(self.cache_service, 'get_cached_file_list'):
                lista_arquivos_do_cache = self.cache_service.get_cached_file_list(lista_arquivos_cache_key)
            else:
                lista_arquivos_do_cache = self.cache_service.get(lista_arquivos_cache_key)
            if lista_arquivos_do_cache is not None:
                print(f"[Reader Geral] CACHE HIT (lista de arquivos): {lista_arquivos_cache_key}")
            else:
                print(f"[Reader Geral] CACHE MISS (lista de arquivos): {lista_arquivos_cache_key}")
        if arquivos_para_ler is not None and self.cache_service:
            print(f"[Reader Geral] Usando cache para leitura de arquivos específicos.")
            arquivos_lidos = {}
            for file_path in arquivos_para_ler:
                cache_key = f"repo_files:{repository_type}:{nome_repo}:{nome_branch}:{file_path}"
                cached_content = self.cache_service.get(cache_key)
                if cached_content is not None:
                    print(f"[Reader Geral] CACHE HIT: {cache_key}")
                    arquivos_lidos[file_path] = cached_content
                else:
                    print(f"[Reader Geral] CACHE MISS: {cache_key}")
                    if repository_type == 'azure':
                        file_content = self.azure_reader.read_single_file(repositorio, file_path, nome_branch)
                    elif repository_type == 'gitlab':
                        file_content = self.gitlab_reader.read_single_file(repositorio, file_path, nome_branch)
                    else:
                        file_content = self.github_reader.read_single_file(repositorio, file_path, nome_branch)
                    arquivos_lidos[file_path] = file_content
                    self.cache_service.set(cache_key, file_content, ttl=cache_ttl)
            resultado = arquivos_lidos
        else:
            if repository_type == 'azure':
                print(f"[Reader Geral] Delegando para Azure Reader")
                resultado = self.azure_reader.read_repository_internal(
                    repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes, retornar_lista_arquivos
                )
            elif repository_type == 'gitlab':
                print(f"[Reader Geral] Delegando para GitLab Reader")
                resultado = self.gitlab_reader.read_repository_internal(
                    repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes, retornar_lista_arquivos
                )
            else:
                print(f"[Reader Geral] Delegando para GitHub Reader")
                resultado = self.github_reader.read_repository_internal(
                    repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes, retornar_lista_arquivos
                )
            if self.cache_service and retornar_lista_arquivos and isinstance(resultado, dict) and 'lista_arquivos' in resultado:
                if lista_arquivos_do_cache is None:
                    if hasattr(self.cache_service, 'set_cached_file_list'):
                        self.cache_service.set_cached_file_list(lista_arquivos_cache_key, resultado['lista_arquivos'], ttl=cache_ttl)
                    else:
                        self.cache_service.set(lista_arquivos_cache_key, resultado['lista_arquivos'], ttl=cache_ttl)
                    print(f"[Reader Geral] Lista de arquivos salva no cache: {lista_arquivos_cache_key}")
                else:
                    print(f"[Reader Geral] Lista de arquivos já estava no cache: {lista_arquivos_cache_key}")
            if self.cache_service and isinstance(resultado, dict):
                codigo_dict = resultado['codigo'] if retornar_lista_arquivos and 'codigo' in resultado else resultado
                for file_path, file_content in codigo_dict.items():
                    cache_key = f"repo_files:{repository_type}:{nome_repo}:{nome_branch}:{file_path}"
                    if self.cache_service.get(cache_key) is not None:
                        print(f"[Reader Geral] CACHE HIT: {cache_key}")
                    else:
                        print(f"[Reader Geral] CACHE MISS: {cache_key}")
                        self.cache_service.set(cache_key, file_content, ttl=cache_ttl)
        if retornar_lista_arquivos and isinstance(resultado, dict) and 'codigo' in resultado:
            print(f"[Reader Geral] Resultado da leitura: {len(resultado['codigo']) if resultado['codigo'] else 0} arquivos de código, {len(resultado.get('lista_arquivos', [])) if resultado.get('lista_arquivos') else 0} arquivos totais")
        else:
            print(f"[Reader Geral] Resultado da leitura: {len(resultado) if resultado else 0} arquivos")
        if not resultado:
            print(f"[Reader Geral] AVISO CRÍTICO: Leitura retornou vazia para repositório {nome_repo} (tipo: {repository_type})")
            print(f"[Reader Geral] Parâmetros: tipo_analise={tipo_analise}, branch={nome_branch}, arquivos_especificos={arquivos_especificos}")
        else:
            if retornar_lista_arquivos and isinstance(resultado, dict) and 'codigo' in resultado:
                arquivos_lidos = resultado['codigo']
                print(f"[Reader Geral] Arquivos lidos com sucesso: {list(arquivos_lidos.keys())[:5]}{'...' if len(arquivos_lidos) > 5 else ''}")
            else:
                print(f"[Reader Geral] Arquivos lidos com sucesso: {list(resultado.keys())[:5]}{'...' if len(resultado) > 5 else ''}")
        return resultado
