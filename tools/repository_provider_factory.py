from typing import Optional
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider

def get_repository_provider(repo_name: str, repository_type: Optional[str] = None) -> IRepositoryProvider:
    if repository_type:
        print(f"Usando repository_type explícito: {repository_type}")
        return get_repository_provider_explicit(repository_type)
    
    if not repo_name or not isinstance(repo_name, str):
        raise ValueError("Nome do repositório deve ser uma string não vazia.")
    
    repo_name = repo_name.strip()
    
    try:
        project_id = int(repo_name)
        print(f"Detectado GitLab Project ID numérico: {project_id}")
        return GitLabRepositoryProvider()
    except ValueError:
        pass
    
    parts = repo_name.split('/')
    
    if len(parts) < 2:
        raise ValueError(
            f"Nome do repositório '{repo_name}' tem formato inválido. "
            "Esperado pelo menos 'org/repo' (2 partes) ou Project ID numérico para GitLab."
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
            org_name.endswith('-team'),
            org_name.count('-') >= 2
        ]
        
        if sum(gitlab_indicators) >= 1:
            print(f"Detectado repositório GitLab por path: {repo_name}")
            return GitLabRepositoryProvider()
        
        print(f"Detectado repositório GitHub: {repo_name}")
        return GitHubRepositoryProvider()
    
    else:
        print(f"Detectado repositório Azure DevOps (path complexo): {repo_name}")
        return AzureRepositoryProvider()

def get_repository_provider_explicit(provider_type: str) -> IRepositoryProvider:
    if not provider_type or not isinstance(provider_type, str):
        raise ValueError("Tipo de provedor deve ser uma string não vazia.")
    
    provider_type = provider_type.lower().strip()
    
    if provider_type == 'github':
        print(f"Criando provedor GitHub explícito")
        return GitHubRepositoryProvider()
    elif provider_type == 'gitlab':
        print(f"Criando provedor GitLab explícito")
        return GitLabRepositoryProvider()
    elif provider_type in ['azure', 'azure_devops']:
        print(f"Criando provedor Azure DevOps explícito")
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

def is_gitlab_project_id(repo_name: str) -> bool:
    try:
        int(repo_name)
        return True
    except ValueError:
        return False