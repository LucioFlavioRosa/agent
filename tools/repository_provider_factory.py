from typing import Optional
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider

def get_repository_provider(repo_name: str) -> IRepositoryProvider:
    if not repo_name or not isinstance(repo_name, str):
        raise ValueError("Nome do repositório deve ser uma string não vazia.")
    
    repo_name = repo_name.strip()
    
    # PRIORIDADE MÁXIMA: Project ID numérico do GitLab
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
    
    # Azure DevOps: exatamente 3 partes
    if len(parts) == 3:
        print(f"Detectado repositório Azure DevOps: {repo_name}")
        return AzureRepositoryProvider()
    
    # 2 partes: GitHub ou GitLab por path - detecção criteriosa
    elif len(parts) == 2:
        org_name, repo_name_only = parts
        
        # Indicadores específicos e robustos de GitLab
        gitlab_indicators = [
            'gitlab' in org_name.lower(),
            'gitlab' in repo_name_only.lower(),
            org_name.endswith('-org'),
            org_name.endswith('-group'),
            org_name.endswith('-team'),
            org_name.count('-') >= 3,  # Namespaces GitLab tendem a ter múltiplos hífens
            len(org_name) > 15 and '-' in org_name  # Namespaces longos com hífen são comuns no GitLab
        ]
        
        # Detecção mais criteriosa: pelo menos 2 indicadores ou 1 forte
        strong_gitlab_indicators = [
            'gitlab' in org_name.lower(),
            'gitlab' in repo_name_only.lower(),
            org_name.endswith('-org'),
            org_name.endswith('-group')
        ]
        
        if any(strong_gitlab_indicators) or sum(gitlab_indicators) >= 2:
            print(f"Detectado repositório GitLab por path: {repo_name}")
            return GitLabRepositoryProvider()
        
        # Padrão: GitHub para formato org/repo simples
        print(f"Detectado repositório GitHub: {repo_name}")
        return GitHubRepositoryProvider()
    
    else:
        # Mais de 3 partes: assume Azure DevOps com path complexo
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