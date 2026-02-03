from typing import Optional
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider

def get_repository_provider_explicit(provider_type: str) -> IRepositoryProvider:
    if not provider_type or not isinstance(provider_type, str):
        raise ValueError("Tipo de provedor deve ser uma string não vazia.")
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
