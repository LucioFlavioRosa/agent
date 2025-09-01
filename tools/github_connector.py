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
        provider_type_name = type(self.repository_provider).__name__.lower()
        print(f"[GitHub Connector] Detectado provider: {provider_type_name}")
        
        if 'github' in provider_type_name:
            token_prefix = 'github-token'
        elif 'gitlab' in provider_type_name:
            token_prefix = 'gitlab-token'
        elif 'azure' in provider_type_name:
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
                print(f"[GitHub Connector] ERRO CRÍTICO: Nenhum token encontrado para provider {provider_type_name}")
                raise ValueError(f"ERRO CRÍTICO: Nenhum token encontrado. Verifique se existe '{token_secret_name}' ou '{token_prefix}' no gerenciador de segredos.") from e
    
    def _is_gitlab_project_id(self, repositorio: str) -> bool:
        try:
            int(repositorio)
            return True
        except ValueError:
            return False
    
    def _extract_org_name(self, repositorio: str) -> str:
        provider_type_name = type(self.repository_provider).__name__.lower()
        
        if 'gitlab' in provider_type_name:
            if self._is_gitlab_project_id(repositorio):
                print(f"[GitHub Connector] GitLab Project ID detectado: {repositorio}. Usando 'gitlab' como org_name para busca de token.")
                return 'gitlab'
            else:
                print(f"[GitHub Connector] GitLab path detectado: {repositorio}. Extraindo namespace para busca de token.")
                try:
                    parts = repositorio.strip().split('/')
                    if len(parts) >= 2:
                        namespace = parts[0]
                        print(f"[GitHub Connector] Namespace GitLab extraído: {namespace}")
                        return namespace
                    else:
                        print(f"[GitHub Connector] Path GitLab inválido. Usando 'gitlab' como fallback.")
                        return 'gitlab'
                except (ValueError, IndexError):
                    print(f"[GitHub Connector] Erro ao extrair namespace do path GitLab. Usando 'gitlab' como fallback.")
                    return 'gitlab'
        
        try:
            org_name = repositorio.strip().split('/')[0]
            print(f"[GitHub Connector] Organização/namespace extraído: {org_name}")
            return org_name
        except (ValueError, IndexError):
            print(f"[GitHub Connector] ERRO: Formato inválido do repositório: {repositorio}")
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio', 'org/proj/repo' ou Project ID numérico para GitLab.")
    
    def _normalize_repository_identifier(self, repositorio: str) -> str:
        provider_type_name = type(self.repository_provider).__name__.lower()
        
        if 'gitlab' in provider_type_name:
            if self._is_gitlab_project_id(repositorio):
                normalized = str(repositorio).strip()
                print(f"[GitHub Connector] GitLab Project ID normalizado: {normalized}")
                return normalized
            else:
                normalized = repositorio.strip()
                print(f"[GitHub Connector] GitLab path normalizado: {normalized}")
                return normalized
        
        return repositorio.strip()
    
    def connection(self, repositorio: str) -> Union[Repository, object]:
        print(f"[GitHub Connector] Iniciando conexão para repositório: {repositorio}")
        print(f"[GitHub Connector] Provider utilizado: {type(self.repository_provider).__name__}")
        
        normalized_repo = self._normalize_repository_identifier(repositorio)
        
        if normalized_repo in self._cached_repos:
            print(f"[GitHub Connector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[normalized_repo]
        
        org_name = self._extract_org_name(normalized_repo)
        token = self._get_token_for_org(org_name)
        print(f"[GitHub Connector] Token obtido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
        try:
            print(f"[GitHub Connector] Tentando acessar repositório '{normalized_repo}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(normalized_repo, token)
            print(f"[GitHub Connector] Repositório '{normalized_repo}' encontrado com sucesso.")
            
        except ValueError as get_error:
            print(f"[GitHub Connector] Repositório '{normalized_repo}' não encontrado. Erro: {get_error}")
            
            provider_name = type(self.repository_provider).__name__
            if 'gitlab' in provider_name.lower():
                if self._is_gitlab_project_id(normalized_repo):
                    print(f"[GitHub Connector] AVISO: Project ID GitLab '{normalized_repo}' não encontrado ou inacessível.")
                    print(f"[GitHub Connector] AVISO: Não é possível criar projeto usando Project ID. Use o formato 'namespace/projeto' para criação.")
                    raise ValueError(f"Projeto GitLab com ID '{normalized_repo}' não encontrado ou inacessível. Verifique o ID e permissões do token. Para criar novos projetos, use o formato 'namespace/projeto'.") from get_error
                else:
                    print(f"[GitHub Connector] Tentando criar projeto GitLab '{normalized_repo}'...")
                    try:
                        repo = self.repository_provider.create_repository(normalized_repo, token)
                        print(f"[GitHub Connector] SUCESSO: Projeto GitLab '{normalized_repo}' criado.")
                    except Exception as create_error:
                        print(f"[GitHub Connector] ERRO: Falha ao criar projeto GitLab '{normalized_repo}': {create_error}")
                        raise ValueError(f"Não foi possível acessar nem criar o projeto GitLab '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
            else:
                print(f"[GitHub Connector] Tentando criar repositório '{normalized_repo}'...")
                try:
                    repo = self.repository_provider.create_repository(normalized_repo, token)
                    print(f"[GitHub Connector] SUCESSO: Repositório '{normalized_repo}' criado.")
                except Exception as create_error:
                    print(f"[GitHub Connector] ERRO: Falha ao criar repositório '{normalized_repo}': {create_error}")
                    raise ValueError(f"Não foi possível acessar nem criar o repositório '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        
        except Exception as unexpected_error:
            print(f"[GitHub Connector] ERRO INESPERADO ao acessar '{normalized_repo}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        
        print(f"[GitHub Connector] Adicionando repositório '{normalized_repo}' ao cache.")
        self._cached_repos[normalized_repo] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConnector':
        return cls(repository_provider=GitHubRepositoryProvider())