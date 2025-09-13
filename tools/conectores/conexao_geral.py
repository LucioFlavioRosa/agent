from typing import Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from domain.interfaces.secret_manager_interface import ISecretManager
from tools.conectores.github_conector import GitHubConector
from tools.conectores.gitlab_conector import GitLabConector
from tools.conectores.azure_conector import AzureConector
from tools.azure_secret_manager import AzureSecretManager

class ConexaoGeral:
    
    def __init__(self, secret_manager: ISecretManager = None):
        self.secret_manager = secret_manager or AzureSecretManager()
        self._conectores_cache = {}
    
    def _get_conector(self, repository_type: str, repository_provider: IRepositoryProvider):
        cache_key = f"{repository_type}:{type(repository_provider).__name__}"
        
        if cache_key not in self._conectores_cache:
            if repository_type == 'github':
                conector = GitHubConector(repository_provider, self.secret_manager)
            elif repository_type == 'gitlab':
                conector = GitLabConector(repository_provider)
            elif repository_type == 'azure':
                conector = AzureConector(repository_provider, self.secret_manager)
            else:
                raise ValueError(f"Tipo de repositório '{repository_type}' não suportado. Tipos válidos: 'github', 'gitlab', 'azure'")
            
            self._conectores_cache[cache_key] = conector
            print(f"[Conexao Geral] Conector {repository_type} criado e cacheado")
        
        return self._conectores_cache[cache_key]
    
    def connection(self, repositorio: str, repository_type: str, repository_provider: IRepositoryProvider) -> Union[object]:
        print(f"[Conexao Geral] Orquestrando conexão para {repository_type}: {repositorio}")
        
        conector = self._get_conector(repository_type, repository_provider)
        return conector.connection(repositorio)
    
    @classmethod
    def create_with_defaults(cls) -> 'ConexaoGeral':
        return cls()
