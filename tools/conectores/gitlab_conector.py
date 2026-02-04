from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import VaultType
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.conectores.base_conector import BaseConector
from tools.conectores.base_token_manager import BaseTokenManager

class GitLabConector(BaseConector):
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None, group_resolver=None):
        super().__init__(repository_provider, secret_manager)
        self.group_resolver = group_resolver
        self.token_manager = BaseTokenManager(vault_type=VaultType.GITHUB, group_resolver=group_resolver)

    def _is_gitlab_project_id(self, repositorio: str) -> bool:
        try:
            int(repositorio)
            return True
        except ValueError:
            return False

    def _extract_org_name(self, repositorio: str) -> str:
        if self._is_gitlab_project_id(repositorio):
            print(f"[GitLab Conector] GitLab Project ID detectado: {repositorio}. Usando 'gitlab' como org_name para busca de token.")
            return 'gitlab'
        else:
            print(f"[GitLab Conector] GitLab path detectado: {repositorio}. Extraindo namespace para busca de token.")
            try:
                parts = repositorio.strip().split('/')
                if len(parts) >= 2:
                    namespace = parts[0]
                    print(f"[GitLab Conector] Namespace GitLab extraído: {namespace}")
                    return namespace
                else:
                    print(f"[GitLab Conector] Path GitLab inválido. Usando 'gitlab' como fallback.")
                    return 'gitlab'
            except (ValueError, IndexError):
                print(f"[GitLab Conector] Erro ao extrair namespace do path GitLab. Usando 'gitlab' como fallback.")
                return 'gitlab'

    def _normalize_repository_identifier(self, repositorio: str) -> str:
        if self._is_gitlab_project_id(repositorio):
            normalized = str(repositorio).strip()
            print(f"[GitLab Conector] GitLab Project ID normalizado: {normalized}")
            return normalized
        else:
            normalized = repositorio.strip()
            print(f"[GitLab Conector] GitLab path normalizado: {normalized}")
            return normalized

    def connection(self, repositorio: str, user_email: str) -> Union[object]:
        normalized_repo = self._normalize_repository_identifier(repositorio)
        org_name = self._extract_org_name(normalized_repo)
        return super()._handle_repository_connection(normalized_repo, "GitLab", org_name, user_email)

    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        return cls(repository_provider=GitLabRepositoryProvider())
