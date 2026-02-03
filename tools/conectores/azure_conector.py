from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.conectores.base_conector import BaseConector

class AzureConector(BaseConector):
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None, group_resolver=None):
        super().__init__(repository_provider, secret_manager or AzureSecretManager())
        self.group_resolver = group_resolver

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

    def _get_token_for_org(self, org_name: str, platform: str, user_email: str) -> str:
        print(f"[{platform} Conector] Buscando token para organização: {org_name} e usuário: {user_email}")
        token_secret_name = f"{platform.lower()}"
        print(f"[{platform} Conector] Tentando buscar token com contexto de grupo: {token_secret_name}")
        try:
            token = self.secret_manager.get_secret_with_user_context(token_secret_name, user_email, group_resolver=self.group_resolver)
            print(f"[{platform} Conector] Token encontrado para grupo e empresa via group_resolver")
            return token
        except Exception as e:
            print(f"[{platform} Conector] ERRO CRÍTICO: Token '{token_secret_name}' não encontrado. Não há fallback.")
            raise ValueError(f"ERRO CRÍTICO: Nenhum token {platform} encontrado para '{token_secret_name}' com grupo. Verifique se existe no gerenciador de segredos.") from e

    def connection(self, repositorio: str, user_email: str) -> Union[object]:
        org_name = self._extract_org_name(repositorio)
        return self._handle_repository_connection(repositorio, "Azure", org_name, user_email)

    def _handle_repository_connection(self, repositorio: str, platform: str, org_name: str, user_email: str) -> Union[object]:
        print(f"[{platform} Conector] Iniciando conexão para repositório {platform}: {repositorio}")
        print(f"[{platform} Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        normalized_repo = repositorio.strip()
        cache_key = f"{platform.lower()}:{normalized_repo}:{user_email}"
        if cache_key in self._cached_repos:
            print(f"[{platform} Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        token = self._get_token_for_org(org_name, platform, user_email)
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
    def create_with_defaults(cls, group_resolver=None) -> 'AzureConector':
        return cls(repository_provider=AzureRepositoryProvider(), group_resolver=group_resolver)
