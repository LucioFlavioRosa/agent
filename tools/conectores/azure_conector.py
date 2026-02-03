from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager, VaultType
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.conectores.base_conector import BaseConector
from utils.constants import PLATFORM_AZURE, TOKEN_MASK
from tools.conectores.base_token_manager import BaseTokenManager

class AzureConector(BaseConector):
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None, group_resolver=None):
        super().__init__(repository_provider, secret_manager or AzureSecretManager())
        self.group_resolver = group_resolver
        self.token_manager = BaseTokenManager(secret_manager_devops=AzureSecretManager(vault_type=VaultType.AZURE_DEVOPS), group_resolver=group_resolver)

    def _parse_repository_name(self, repository_name: str) -> tuple:
        parts = repository_name.split('/')
        if len(parts) != 3:
            raise ValueError(
                f"Nome do repositório '{repository_name}' tem formato inválido. "
                "Esperado 'organization/project/repository'."
            )
        return parts[0], parts[1], parts[2]

    def _extract_org_name(self, repositorio: str) -> str:
        try:
            organization, project, repo_name = self._parse_repository_name(repositorio)
            print(f"[Azure Conector] Organização Azure extraída: {organization}")
            return organization
        except ValueError as e:
            print(f"[Azure Conector] ERRO: {e}")
            raise

    def connection(self, repositorio: str, user_email: str) -> Union[object]:
        org_name = self._extract_org_name(repositorio)
        return super()._handle_repository_connection(repositorio, PLATFORM_AZURE, org_name, user_email)

    @classmethod
    def create_with_defaults(cls, group_resolver=None) -> 'AzureConector':
        return cls(repository_provider=AzureRepositoryProvider(), group_resolver=group_resolver)
