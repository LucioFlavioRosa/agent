from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.azure_repository_provider import AzureRepositoryProvider

class AzureConector:
    _cached_repos: Dict[str, Union[object]] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str) -> str:
        print(f"[Azure Conector] Buscando token para organização: {org_name}")
        
        token_secret_name = f"azure-token-{org_name}"
        print(f"[Azure Conector] Tentando buscar token específico: {token_secret_name}")
        
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[Azure Conector] Token específico encontrado para {org_name}")
            return token
        except ValueError:
            print(f"[Azure Conector] Token específico '{token_secret_name}' não encontrado. Tentando token padrão 'azure-token'.")
            try:
                token = self.secret_manager.get_secret('azure-token')
                print(f"[Azure Conector] Token padrão 'azure-token' encontrado")
                return token
            except ValueError as e:
                print(f"[Azure Conector] ERRO CRÍTICO: Nenhum token Azure encontrado")
                raise ValueError(f"ERRO CRÍTICO: Nenhum token Azure encontrado. Verifique se existe '{token_secret_name}' ou 'azure-token' no gerenciador de segredos.") from e
    
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
        print(f"[Azure Conector] Iniciando conexão para repositório Azure DevOps: {repositorio}")
        print(f"[Azure Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        
        normalized_repo = repositorio.strip()
        cache_key = f"azure:{normalized_repo}"
        
        if cache_key in self._cached_repos:
            print(f"[Azure Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        
        org_name = self._extract_org_name(normalized_repo)
        token = self._get_token_for_org(org_name)
        print(f"[Azure Conector] Token obtido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
        try:
            print(f"[Azure Conector] Tentando acessar repositório '{normalized_repo}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(normalized_repo, token)
            print(f"[Azure Conector] Repositório '{normalized_repo}' encontrado com sucesso.")
            
        except ValueError as get_error:
            print(f"[Azure Conector] Repositório '{normalized_repo}' não encontrado. Erro: {get_error}")
            print(f"[Azure Conector] Tentando criar repositório '{normalized_repo}'...")
            try:
                repo = self.repository_provider.create_repository(normalized_repo, token)
                print(f"[Azure Conector] SUCESSO: Repositório '{normalized_repo}' criado.")
            except Exception as create_error:
                print(f"[Azure Conector] ERRO: Falha ao criar repositório '{normalized_repo}': {create_error}")
                raise ValueError(f"Não foi possível acessar nem criar o repositório '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        
        except Exception as unexpected_error:
            print(f"[Azure Conector] ERRO INESPERADO ao acessar '{normalized_repo}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        
        print(f"[Azure Conector] Adicionando repositório '{normalized_repo}' ao cache com chave '{cache_key}'.")
        self._cached_repos[cache_key] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'AzureConector':
        return cls(repository_provider=AzureRepositoryProvider())