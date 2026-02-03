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
        return self._handle_repository_connection(repositorio, "GitHub", org_name, user_email)

    def _handle_repository_connection(self, repositorio: str, platform: str, org_name: str, user_email: str) -> Union[object]:
        print(f"[{platform} Conector] Iniciando conexão para repositório {platform}: {repositorio}")
        print(f"[{platform} Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        normalized_repo = repositorio.strip()
        cache_key = f"{platform.lower()}:{normalized_repo}:{user_email}"
        if cache_key in self._cached_repos:
            print(f"[{platform} Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        token = self.token_manager.get_token(platform, org_name, user_email)
        masked_token = self._TOKEN_MASK + token[-4:] if len(token) > 4 else self._TOKEN_MASK
        print(f"[{platform} Conector] Token obtido: {masked_token}")
        try:
            print(f"[{platform} Conector] Tentando acessar repositório '{normalized_repo}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(normalized_repo, token)
            print(f"[{platform} Conector] Repositório '{normalized_repo}' encontrado com sucesso.")
        except ValueError as get_error:
            print(f"[{platform} Conector] Repositório '{normalized_repo}' não encontrado. Erro: {get_error}")
            print(f"[{platform} Conector] Tentando criar repositório '{normalized_repo}'...")
            try:
                repo = self.repository_provider.create_repository(normalized_repo, token)
                print(f"[{platform} Conector] SUCESSO: Repositório '{normalized_repo}' criado.")
            except Exception as create_error:
                print(f"[{platform} Conector] ERRO: Falha ao criar repositório '{normalized_repo}': {create_error}")
                raise ValueError(f"Não foi possível acessar nem criar o repositório '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        except Exception as unexpected_error:
            print(f"[{platform} Conector] ERRO INESPERADO ao acessar '{normalized_repo}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        print(f"[{platform} Conector] Adicionando repositório '{normalized_repo}' ao cache com chave '{cache_key}'.")
        self._cached_repos[cache_key] = repo
        return repo

    @classmethod
    def create_with_defaults(cls) -> 'GitHubConector':
        return cls(repository_provider=GitHubRepositoryProvider())
