from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.conectores.base_conector import BaseConector

class GitLabConector(BaseConector):
    
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
    
    def connection(self, repositorio: str) -> Union[object]:
        normalized_repo = self._normalize_repository_identifier(repositorio)
        org_name = self._extract_org_name(normalized_repo)
        
        try:
            return self._handle_repository_connection(normalized_repo, "GitLab", org_name)
        except ValueError as get_error:
            if self._is_gitlab_project_id(normalized_repo):
                print(f"[GitLab Conector] AVISO: Project ID GitLab '{normalized_repo}' não encontrado ou inacessível.")
                print(f"[GitLab Conector] AVISO: Não é possível criar projeto usando Project ID. Use o formato 'namespace/projeto' para criação.")
                raise ValueError(f"Projeto GitLab com ID '{normalized_repo}' não encontrado ou inacessível. Verifique o ID e permissões do token. Para criar novos projetos, use o formato 'namespace/projeto'.") from get_error
            else:
                print(f"[GitLab Conector] Tentativa de busca por nome completo falhou. Detalhes: {get_error}")
                print(f"[GitLab Conector] Dica: Verifique se o formato está correto ('namespace/projeto') ou tente usar o Project ID numérico.")
                raise
    
    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        return cls(repository_provider=GitLabRepositoryProvider())