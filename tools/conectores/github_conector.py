from github import Repository
from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.conectores.base_conector import BaseConector

class GitHubConector(BaseConector):
    
    def _extract_org_name(self, repositorio: str) -> str:
        try:
            org_name = repositorio.strip().split('/')[0]
            print(f"[GitHub Conector] Organização extraída: {org_name}")
            return org_name
        except (ValueError, IndexError):
            print(f"[GitHub Conector] ERRO: Formato inválido do repositório: {repositorio}")
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")
    
    def connection(self, repositorio: str) -> Union[Repository, object]:
        org_name = self._extract_org_name(repositorio)
        return self._handle_repository_connection(repositorio, "GitHub", org_name)
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConector':
        return cls(repository_provider=GitHubRepositoryProvider())