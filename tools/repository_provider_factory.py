from typing import Optional
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider

def get_repository_provider(repo_name: str) -> IRepositoryProvider:
    if not repo_name or not isinstance(repo_name, str):
        raise ValueError("Nome do repositório deve ser uma string não vazia.")
    
    repo_name = repo_name.strip()
    parts = repo_name.split('/')
    
    if len(parts) < 2:
        raise ValueError(
            f"Nome do repositório '{repo_name}' tem formato inválido. "
            "Esperado pelo menos 'org/repo' (2 partes)."
        )
    
    if len(parts) == 3:
        print(f"Detectado repositório Azure DevOps: {repo_name}")
        return AzureRepositoryProvider()
    
    elif len(parts) == 2:
        org_name, repo_name_only = parts
        
        gitlab_indicators = [
            'gitlab' in org_name.lower(),
            'gitlab' in repo_name_only.lower(),
            '-' in org_name and len(org_name) > 10,
            org_name.endswith('-org'),
            org_name.endswith('-group'),
            org_name.endswith('-team')
        ]
        
        if sum(gitlab_indicators) >= 1:
            print(f"Detectado repositório GitLab: {repo_name}")
            return GitLabRepositoryProvider()
        
        print(f"Detectado repositório GitHub: {repo_name}")
        return GitHubRepositoryProvider()
    
    else:
        print(f"Detectado repositório Azure DevOps (path complexo): {repo_name}")
        return AzureRepositoryProvider()

def get_repository_provider_explicit(provider_type: str) -> IRepositoryProvider:
    provider_type = provider_type.lower().strip()
    
    if provider_type == 'github':
        return GitHubRepositoryProvider()
    elif provider_type == 'gitlab':
        return GitLabRepositoryProvider()
    elif provider_type in ['azure', 'azure_devops']:
        return AzureRepositoryProvider()
    else:
        raise ValueError(
            f"Tipo de provedor '{provider_type}' não reconhecido. "
            "Valores aceitos: 'github', 'gitlab', 'azure', 'azure_devops'."
        )

def detect_repository_type(repo_name: str) -> str:
    provider = get_repository_provider(repo_name)
    
    if isinstance(provider, GitHubRepositoryProvider):
        return 'github'
    elif isinstance(provider, GitLabRepositoryProvider):
        return 'gitlab'
    elif isinstance(provider, AzureRepositoryProvider):
        return 'azure'
    else:
        return 'unknown'