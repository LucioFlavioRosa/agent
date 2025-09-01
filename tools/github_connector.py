from github import Repository
from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubConnector:
    _cached_repos: Dict[str, Union[Repository, object]] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str) -> str:
        provider_type = type(self.repository_provider).__name__.lower()
        
        if 'github' in provider_type:
            token_prefix = 'github-token'
        elif 'gitlab' in provider_type:
            token_prefix = 'gitlab-token'
        elif 'azure' in provider_type:
            token_prefix = 'azure-token'
        else:
            token_prefix = 'repo-token'
        
        token_secret_name = f"{token_prefix}-{org_name}"
        
        try:
            return self.secret_manager.get_secret(token_secret_name)
        except ValueError:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Tentando usar token padrão '{token_prefix}'.")
            try:
                return self.secret_manager.get_secret(token_prefix)
            except ValueError as e:
                raise ValueError(f"ERRO CRÍTICO: Nenhum token encontrado. Verifique se existe '{token_secret_name}' ou '{token_prefix}' no gerenciador de segredos.") from e
    
    def connection(self, repositorio: str) -> Union[Repository, object]:
        if repositorio in self._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            return self._cached_repos[repositorio]
        
        try:
            org_name = repositorio.split('/')[0]
        except (ValueError, IndexError):
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio' ou 'org/proj/repo'.")
        
        token = self._get_token_for_org(org_name)
        
        try:
            print(f"Tentando acessar o repositório '{repositorio}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(repositorio, token)
            print(f"Repositório '{repositorio}' encontrado com sucesso.")
        except ValueError:
            print(f"AVISO: Repositório '{repositorio}' não encontrado. Tentando criá-lo...")
            repo = self.repository_provider.create_repository(repositorio, token)
            print(f"SUCESSO: Repositório '{repositorio}' criado.")
        
        self._cached_repos[repositorio] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConnector':
        return cls(repository_provider=GitHubRepositoryProvider())