from github import Repository
from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubConector:
    _cached_repos: Dict[str, Union[Repository, object]] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str) -> str:
        print(f"[GitHub Conector] Buscando token para organização: {org_name}")
        
        token_secret_name = f"github-token-{org_name}"
        print(f"[GitHub Conector] Tentando buscar token específico: {token_secret_name}")
        
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[GitHub Conector] Token específico encontrado para {org_name}")
            return token
        except ValueError:
            print(f"[GitHub Conector] Token específico '{token_secret_name}' não encontrado. Tentando token padrão 'github-token'.")
            try:
                token = self.secret_manager.get_secret('github-token')
                print(f"[GitHub Conector] Token padrão 'github-token' encontrado")
                return token
            except ValueError as e:
                print(f"[GitHub Conector] ERRO CRÍTICO: Nenhum token GitHub encontrado")
                raise ValueError(f"ERRO CRÍTICO: Nenhum token GitHub encontrado. Verifique se existe '{token_secret_name}' ou 'github-token' no gerenciador de segredos.") from e
    
    def _extract_org_name(self, repositorio: str) -> str:
        try:
            org_name = repositorio.strip().split('/')[0]
            print(f"[GitHub Conector] Organização extraída: {org_name}")
            return org_name
        except (ValueError, IndexError):
            print(f"[GitHub Conector] ERRO: Formato inválido do repositório: {repositorio}")
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")
    
    def connection(self, repositorio: str) -> Union[Repository, object]:
        print(f"[GitHub Conector] Iniciando conexão para repositório GitHub: {repositorio}")
        print(f"[GitHub Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        
        normalized_repo = repositorio.strip()
        cache_key = f"github:{normalized_repo}"
        
        if cache_key in self._cached_repos:
            print(f"[GitHub Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        
        org_name = self._extract_org_name(normalized_repo)
        token = self._get_token_for_org(org_name)
        print(f"[GitHub Conector] Token obtido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
        try:
            print(f"[GitHub Conector] Tentando acessar repositório '{normalized_repo}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(normalized_repo, token)
            print(f"[GitHub Conector] Repositório '{normalized_repo}' encontrado com sucesso.")
            
        except ValueError as get_error:
            print(f"[GitHub Conector] Repositório '{normalized_repo}' não encontrado. Erro: {get_error}")
            print(f"[GitHub Conector] Tentando criar repositório '{normalized_repo}'...")
            try:
                repo = self.repository_provider.create_repository(normalized_repo, token)
                print(f"[GitHub Conector] SUCESSO: Repositório '{normalized_repo}' criado.")
            except Exception as create_error:
                print(f"[GitHub Conector] ERRO: Falha ao criar repositório '{normalized_repo}': {create_error}")
                raise ValueError(f"Não foi possível acessar nem criar o repositório '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        
        except Exception as unexpected_error:
            print(f"[GitHub Conector] ERRO INESPERADO ao acessar '{normalized_repo}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        
        print(f"[GitHub Conector] Adicionando repositório '{normalized_repo}' ao cache com chave '{cache_key}'.")
        self._cached_repos[cache_key] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConector':
        return cls(repository_provider=GitHubRepositoryProvider())