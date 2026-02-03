from github import Repository
from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import VaultType
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.conectores.base_conector import BaseConector
from tools.conectores.base_token_manager import BaseTokenManager

class GitHubConector(BaseConector):
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None, group_resolver=None):
        super().__init__(repository_provider, secret_manager)
        self.group_resolver = group_resolver
        self.token_manager = BaseTokenManager(vault_type=VaultType.GITHUB, group_resolver=group_resolver)

    def _extract_org_name(self, repositorio: str) -> str:
        try:
            org_name = repositorio.strip().split('/')[0]
            print(f"[GitHub Conector] Organização extraída: {org_name}")
            return org_name
        except (ValueError, IndexError):
            print(f"[GitHub Conector] ERRO: Formato inválido do repositório: {repositorio}")
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")

    def connection(self, repositorio: str, user_email: str) -> Union[Repository, object]:
        org_name = self._extract_org_name(repositorio)
        return super()._handle_repository_connection(repositorio, "GitHub", org_name, user_email)

    @classmethod
    def create_with_defaults(cls) -> 'GitHubConector':
        return cls(repository_provider=GitHubRepositoryProvider())
