from typing import Dict, Union, Optional
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager

class BaseConector:
    _cached_repos: Dict[str, Union[object]] = {}
    _TOKEN_MASK = '***'
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None, group_resolver: Optional[object] = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
        self.group_resolver = group_resolver
    
    def _get_token_for_org(self, platform: str, user_email: str) -> str:
        print(f"[{platform} Conector] Buscando token para usuário: {user_email}")
        token_secret_name = f"{platform.lower()}-token"
        print(f"[{platform} Conector] Tentando buscar token com contexto de usuário: {token_secret_name}, {user_email}")
        token = self.secret_manager.get_secret_with_user_context(token_secret_name, user_email, group_resolver=self.group_resolver)
        print(f"[{platform} Conector] Token encontrado para usuário {user_email}")
        return token
    
    def _handle_repository_connection(self, repositorio: str, platform: str, org_name: str, user_email: str) -> Union[object]:
        print(f"[{platform} Conector] Iniciando conexão para repositório {platform}: {repositorio}")
        print(f"[{platform} Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        normalized_repo = repositorio.strip()
        cache_key = f"{platform.lower()}:{normalized_repo}:{user_email}"
        if cache_key in self._cached_repos:
            print(f"[{platform} Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        token = self._get_token_for_org(platform, user_email)
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
