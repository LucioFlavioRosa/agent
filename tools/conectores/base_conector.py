from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager

class BaseConector:
    _cached_repos: Dict[str, Union[object]] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str, platform: str) -> str:
        print(f"[{platform} Conector] Buscando token para organização: {org_name}")
        
        token_secret_name = f"{platform.lower()}-token-{org_name}"
        print(f"[{platform} Conector] Tentando buscar token específico: {token_secret_name}")
        
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[{platform} Conector] Token específico encontrado para {org_name}")
            return token
        except ValueError:
            print(f"[{platform} Conector] Token específico '{token_secret_name}' não encontrado. Tentando token padrão '{platform.lower()}-token'.")
            try:
                token = self.secret_manager.get_secret(f'{platform.lower()}-token')
                print(f"[{platform} Conector] Token padrão '{platform.lower()}-token' encontrado")
                return token
            except ValueError as e:
                print(f"[{platform} Conector] ERRO CRÍTICO: Nenhum token {platform} encontrado")
                raise ValueError(f"ERRO CRÍTICO: Nenhum token {platform} encontrado. Verifique se existe '{token_secret_name}' ou '{platform.lower()}-token' no gerenciador de segredos.") from e
    
    def _handle_repository_connection(self, repositorio: str, platform: str, org_name: str) -> Union[object]:
        print(f"[{platform} Conector] Iniciando conexão para repositório {platform}: {repositorio}")
        print(f"[{platform} Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        
        normalized_repo = repositorio.strip()
        cache_key = f"{platform.lower()}:{normalized_repo}"
        
        if cache_key in self._cached_repos:
            print(f"[{platform} Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        
        token = self._get_token_for_org(org_name, platform)
        print(f"[{platform} Conector] Token obtido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
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