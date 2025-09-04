import time
import yaml
import os
from typing import Dict, Optional, List
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.conectores.conexao_geral import ConexaoGeral
from .github_reader import GitHubReader
from .gitlab_reader import GitLabReader
from .azure_reader import AzureReader

class ReaderGeral(IRepositoryReader):
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()
        
        self.github_reader = GitHubReader(repository_provider)
        self.gitlab_reader = GitLabReader(repository_provider)
        self.azure_reader = AzureReader(repository_provider)

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

    def _identificar_tipo_repositorio(self, repositorio):
        if isinstance(repositorio, dict) and repositorio.get('_provider_type') == 'azure_devops':
            return 'azure'
        elif hasattr(repositorio, 'web_url') or 'gitlab' in str(type(repositorio)).lower():
            return 'gitlab'
        else:
            return 'github'

    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        provider_name = type(self.repository_provider).__name__
        print(f"Iniciando leitura do repositório: {nome_repo} via {provider_name}")

        conexao_geral = ConexaoGeral.create_with_defaults()
        
        repository_type = 'github'
        if 'GitLab' in provider_name:
            repository_type = 'gitlab'
        elif 'Azure' in provider_name:
            repository_type = 'azure'
        
        repositorio = conexao_geral.connection(repositorio=nome_repo, repository_type=repository_type, repository_provider=self.repository_provider)
        tipo_repo_identificado = self._identificar_tipo_repositorio(repositorio)
        
        if tipo_repo_identificado == 'azure':
            return self.azure_reader.read_repository_internal(
                repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes
            )
        elif tipo_repo_identificado == 'gitlab':
            return self.gitlab_reader.read_repository_internal(
                repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes
            )
        else:
            return self.github_reader.read_repository_internal(
                repositorio, tipo_analise, nome_branch, arquivos_especificos, self._mapeamento_tipo_extensoes
            )