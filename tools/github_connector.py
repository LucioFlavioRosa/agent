from github import Repository
from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubConnector:
    _cached_repos: Dict[str, Union[Repository, object]] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str) -> str:
        provider_type = type(self.repository_provider).__name__.lower()
        print(f"[GitHub Connector] Detectado provider: {provider_type}")
        
        if 'github' in provider_type:
            token_prefix = 'github-token'
        elif 'gitlab' in provider_type:
            token_prefix = 'gitlab-token'
        elif 'azure' in provider_type:
            token_prefix = 'azure-token'
        else:
            token_prefix = 'repo-token'
        
        token_secret_name = f"{token_prefix}-{org_name}"
        print(f"[GitHub Connector] Tentando buscar token específico: {token_secret_name}")
        
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[GitHub Connector] Token específico encontrado para {org_name}")
            return token
        except ValueError:
            print(f"[GitHub Connector] Token específico '{token_secret_name}' não encontrado. Tentando token padrão '{token_prefix}'.")
            try:
                token = self.secret_manager.get_secret(token_prefix)
                print(f"[GitHub Connector] Token padrão '{token_prefix}' encontrado")
                return token
            except ValueError as e:
                print(f"[GitHub Connector] ERRO CRÍTICO: Nenhum token encontrado para provider {provider_type}")
                raise ValueError(f"ERRO CRÍTICO: Nenhum token encontrado. Verifique se existe '{token_secret_name}' ou '{token_prefix}' no gerenciador de segredos.") from e
    
    def _extract_org_name(self, repositorio: str) -> str:
        provider_type = type(self.repository_provider).__name__.lower()
        
        if 'gitlab' in provider_type:
            try:
                int(repositorio)
                print(f"[GitHub Connector] GitLab project ID detectado: {repositorio}. Usando 'gitlab' como org_name para token.")
                return 'gitlab'
            except ValueError:
                pass
        
        try:
            org_name = repositorio.split('/')[0]
            print(f"[GitHub Connector] Organização/namespace extraído: {org_name}")
            return org_name
        except (ValueError, IndexError):
            print(f"[GitHub Connector] ERRO: Formato inválido do repositório: {repositorio}")
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio' ou 'org/proj/repo'.")
    
    def connection(self, repositorio: str) -> Union[Repository, object]:
        print(f"[GitHub Connector] Iniciando conexão para repositório: {repositorio}")
        print(f"[GitHub Connector] Provider utilizado: {type(self.repository_provider).__name__}")
        
        if repositorio in self._cached_repos:
            print(f"[GitHub Connector] Retornando repositório '{repositorio}' do cache.")
            return self._cached_repos[repositorio]
        
        org_name = self._extract_org_name(repositorio)
        token = self._get_token_for_org(org_name)
        print(f"[GitHub Connector] Token obtido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
        try:
            print(f"[GitHub Connector] Tentando acessar repositório '{repositorio}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(repositorio, token)
            print(f"[GitHub Connector] Repositório '{repositorio}' encontrado com sucesso.")
            
        except ValueError as get_error:
            print(f"[GitHub Connector] Repositório '{repositorio}' não encontrado. Erro: {get_error}")
            
            provider_name = type(self.repository_provider).__name__
            if 'gitlab' in provider_name.lower():
                print(f"[GitHub Connector] AVISO: Para repositórios GitLab, verifique se o nome está correto e se o token possui permissões adequadas.")
                print(f"[GitHub Connector] AVISO: Não tentando criar repositório GitLab automaticamente.")
                raise ValueError(f"Repositório GitLab '{repositorio}' não encontrado ou inacessível. Verifique o nome e permissões.") from get_error
            
            print(f"[GitHub Connector] Tentando criar repositório '{repositorio}'...")
            try:
                repo = self.repository_provider.create_repository(repositorio, token)
                print(f"[GitHub Connector] SUCESSO: Repositório '{repositorio}' criado.")
            except Exception as create_error:
                print(f"[GitHub Connector] ERRO: Falha ao criar repositório '{repositorio}': {create_error}")
                raise ValueError(f"Não foi possível acessar nem criar o repositório '{repositorio}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        
        except Exception as unexpected_error:
            print(f"[GitHub Connector] ERRO INESPERADO ao acessar '{repositorio}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        
        print(f"[GitHub Connector] Adicionando repositório '{repositorio}' ao cache.")
        self._cached_repos[repositorio] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConnector':
        return cls(repository_provider=GitHubRepositoryProvider())