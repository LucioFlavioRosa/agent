from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.conectores.base_conector import BaseConector

class AzureConector(BaseConector):
    
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
    
    def connection(self, repositorio: str) -> Union[object]:
        org_name = self._extract_org_name(repositorio)
        return self._handle_repository_connection(repositorio, "Azure", org_name)
    
    @classmethod
    def create_with_defaults(cls) -> 'AzureConector':
        return cls(repository_provider=AzureRepositoryProvider())