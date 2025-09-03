from typing import Dict, Union
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.gitlab_repository_provider import GitLabRepositoryProvider

class GitLabConector:
    _cached_repos: Dict[str, Union[object]] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str) -> str:
        print(f"[GitLab Conector] Buscando token para organização/namespace: {org_name}")
        
        token_secret_name = f"gitlab-token-{org_name}"
        print(f"[GitLab Conector] Tentando buscar token específico: {token_secret_name}")
        
        try:
            token = self.secret_manager.get_secret(token_secret_name)
            print(f"[GitLab Conector] Token específico encontrado para {org_name}")
            return token
        except ValueError:
            print(f"[GitLab Conector] Token específico '{token_secret_name}' não encontrado. Tentando token padrão 'gitlab-token'.")
            try:
                token = self.secret_manager.get_secret('gitlab-token')
                print(f"[GitLab Conector] Token padrão 'gitlab-token' encontrado")
                return token
            except ValueError as e:
                print(f"[GitLab Conector] ERRO CRÍTICO: Nenhum token GitLab encontrado")
                raise ValueError(f"ERRO CRÍTICO: Nenhum token GitLab encontrado. Verifique se existe '{token_secret_name}' ou 'gitlab-token' no gerenciador de segredos.") from e
    
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
        print(f"[GitLab Conector] Iniciando conexão para repositório GitLab: {repositorio}")
        print(f"[GitLab Conector] Provider utilizado: {type(self.repository_provider).__name__}")
        
        normalized_repo = self._normalize_repository_identifier(repositorio)
        cache_key = f"gitlab:{normalized_repo}"
        
        if cache_key in self._cached_repos:
            print(f"[GitLab Conector] Retornando repositório '{normalized_repo}' do cache.")
            return self._cached_repos[cache_key]
        
        org_name = self._extract_org_name(normalized_repo)
        token = self._get_token_for_org(org_name)
        print(f"[GitLab Conector] Token obtido: {'***' + token[-4:] if len(token) > 4 else '***'}")
        
        try:
            print(f"[GitLab Conector] Tentando acessar repositório '{normalized_repo}' via {type(self.repository_provider).__name__}...")
            repo = self.repository_provider.get_repository(normalized_repo, token)
            print(f"[GitLab Conector] Repositório '{normalized_repo}' encontrado com sucesso.")
            
        except ValueError as get_error:
            print(f"[GitLab Conector] Repositório '{normalized_repo}' não encontrado. Erro: {get_error}")
            
            if self._is_gitlab_project_id(normalized_repo):
                print(f"[GitLab Conector] AVISO: Project ID GitLab '{normalized_repo}' não encontrado ou inacessível.")
                print(f"[GitLab Conector] AVISO: Não é possível criar projeto usando Project ID. Use o formato 'namespace/projeto' para criação.")
                raise ValueError(f"Projeto GitLab com ID '{normalized_repo}' não encontrado ou inacessível. Verifique o ID e permissões do token. Para criar novos projetos, use o formato 'namespace/projeto'.") from get_error
            else:
                print(f"[GitLab Conector] Tentando criar projeto GitLab '{normalized_repo}'...")
                try:
                    repo = self.repository_provider.create_repository(normalized_repo, token)
                    print(f"[GitLab Conector] SUCESSO: Projeto GitLab '{normalized_repo}' criado.")
                except Exception as create_error:
                    print(f"[GitLab Conector] ERRO: Falha ao criar projeto GitLab '{normalized_repo}': {create_error}")
                    raise ValueError(f"Não foi possível acessar nem criar o projeto GitLab '{normalized_repo}'. Erro original: {get_error}. Erro de criação: {create_error}") from create_error
        
        except Exception as unexpected_error:
            print(f"[GitLab Conector] ERRO INESPERADO ao acessar '{normalized_repo}': {type(unexpected_error).__name__}: {unexpected_error}")
            raise
        
        print(f"[GitLab Conector] Adicionando repositório '{normalized_repo}' ao cache com chave '{cache_key}'.")
        self._cached_repos[cache_key] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        return cls(repository_provider=GitLabRepositoryProvider())