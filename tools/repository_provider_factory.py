from typing import Optional
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider

def get_repository_provider(repo_name: str) -> IRepositoryProvider:
    """
    Factory function que retorna o provedor de repositório apropriado baseado no nome do repositório.
    
    Esta função implementa a lógica de detecção automática do tipo de repositório
    baseada em padrões de nomenclatura específicos de cada provedor:
    
    - GitHub: formato 'org/repo' (2 partes)
    - GitLab: formato 'grupo/projeto' (2 partes, mas com características específicas)
    - Azure DevOps: formato 'organization/project/repository' (3 partes)
    
    A detecção segue uma estratégia hierárquica:
    1. Se tem 3 partes → Azure DevOps
    2. Se tem 2 partes → analisa características para distinguir GitHub vs GitLab
    3. Fallback para GitHub como padrão mais comum
    
    Args:
        repo_name (str): Nome do repositório no formato específico do provedor.
            Exemplos:
            - GitHub: 'microsoft/vscode', 'facebook/react'
            - GitLab: 'gitlab-org/gitlab', 'grupo-empresa/projeto-interno'
            - Azure: 'myorg/myproject/myrepo'
    
    Returns:
        IRepositoryProvider: Instância do provedor apropriado (GitHub, GitLab ou Azure)
    
    Raises:
        ValueError: Se o formato do nome do repositório for inválido (menos de 2 partes)
        
    Example:
        >>> # Detecção automática do provedor
        >>> provider = get_repository_provider("microsoft/vscode")  # GitHub
        >>> provider = get_repository_provider("gitlab-org/gitlab")  # GitLab
        >>> provider = get_repository_provider("myorg/proj/repo")   # Azure DevOps
        >>> 
        >>> # Uso com connector
        >>> connector = GitHubConnector(repository_provider=provider)
    
    Note:
        - A detecção é baseada em heurísticas de nomenclatura
        - Para casos ambíguos entre GitHub e GitLab, usa GitHub como padrão
        - Extensível para novos provedores adicionando novas condições
        - Não faz validação de existência do repositório (responsabilidade do provider)
    """
    if not repo_name or not isinstance(repo_name, str):
        raise ValueError("Nome do repositório deve ser uma string não vazia.")
    
    # Remove espaços e normaliza o nome
    repo_name = repo_name.strip()
    
    # Divide o nome em partes para análise
    parts = repo_name.split('/')
    
    if len(parts) < 2:
        raise ValueError(
            f"Nome do repositório '{repo_name}' tem formato inválido. "
            "Esperado pelo menos 'org/repo' (2 partes)."
        )
    
    # REGRA 1: Azure DevOps - formato com 3 partes
    if len(parts) == 3:
        print(f"Detectado repositório Azure DevOps: {repo_name}")
        return AzureRepositoryProvider()
    
    # REGRA 2: GitHub vs GitLab - formato com 2 partes
    elif len(parts) == 2:
        org_name, repo_name_only = parts
        
        # Heurísticas para distinguir GitLab de GitHub
        gitlab_indicators = [
            'gitlab' in org_name.lower(),
            'gitlab' in repo_name_only.lower(),
            '-' in org_name and len(org_name) > 10,  # Grupos GitLab tendem a ter nomes mais longos com hífens
            org_name.endswith('-org'),
            org_name.endswith('-group')
        ]
        
        # Se pelo menos 2 indicadores apontam para GitLab, usa GitLab
        if sum(gitlab_indicators) >= 2:
            print(f"Detectado repositório GitLab: {repo_name}")
            return GitLabRepositoryProvider()
        
        # Padrão: GitHub (mais comum)
        print(f"Detectado repositório GitHub: {repo_name}")
        return GitHubRepositoryProvider()
    
    # REGRA 3: Mais de 3 partes - trata como Azure DevOps com path complexo
    else:
        print(f"Detectado repositório Azure DevOps (path complexo): {repo_name}")
        return AzureRepositoryProvider()

def get_repository_provider_explicit(provider_type: str) -> IRepositoryProvider:
    """
    Factory function para criação explícita de provedores por tipo.
    
    Esta função complementar permite especificar explicitamente o tipo de provedor
    quando a detecção automática não for adequada ou quando se conhece o tipo.
    
    Args:
        provider_type (str): Tipo do provedor. Valores aceitos:
            - 'github': Para repositórios GitHub
            - 'gitlab': Para repositórios GitLab
            - 'azure': Para repositórios Azure DevOps
            - 'azure_devops': Alias para 'azure'
    
    Returns:
        IRepositoryProvider: Instância do provedor especificado
    
    Raises:
        ValueError: Se provider_type não for reconhecido
    
    Example:
        >>> # Criação explícita quando se conhece o tipo
        >>> github_provider = get_repository_provider_explicit('github')
        >>> gitlab_provider = get_repository_provider_explicit('gitlab')
        >>> azure_provider = get_repository_provider_explicit('azure')
    
    Note:
        - Útil para casos onde a detecção automática pode falhar
        - Permite override manual do tipo de provedor
        - Mantém consistência com a factory automática
    """
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
    """
    Função utilitária que retorna apenas o tipo detectado sem instanciar o provedor.
    
    Útil para logging, debugging ou quando se precisa apenas saber o tipo
    sem criar a instância do provedor.
    
    Args:
        repo_name (str): Nome do repositório
    
    Returns:
        str: Tipo detectado ('github', 'gitlab', 'azure')
    
    Example:
        >>> tipo = detect_repository_type("microsoft/vscode")
        >>> print(f"Tipo detectado: {tipo}")  # "Tipo detectado: github"
    """
    # Reutiliza a lógica da factory principal
    provider = get_repository_provider(repo_name)
    
    if isinstance(provider, GitHubRepositoryProvider):
        return 'github'
    elif isinstance(provider, GitLabRepositoryProvider):
        return 'gitlab'
    elif isinstance(provider, AzureRepositoryProvider):
        return 'azure'
    else:
        return 'unknown'