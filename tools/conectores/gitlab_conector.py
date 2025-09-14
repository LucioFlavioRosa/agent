from typing import Union
from .base_conector import BaseConector
from tools.gitlab_repository_provider import GitLabRepositoryProvider

class GitLabConector(BaseConector):
    """
    Conector para o GitLab.
    Esta classe atua como um adaptador, delegando a lógica real para o GitLabRepositoryProvider.
    """
    def __init__(self, repository_provider: GitLabRepositoryProvider):
        """Inicializa o conector com um provider GitLab."""
        if not isinstance(repository_provider, GitLabRepositoryProvider):
            raise TypeError("repository_provider deve ser uma instância de GitLabRepositoryProvider.")
        super().__init__(repository_provider=repository_provider)

    def connection(self, repositorio: str) -> Union[object]:
        """
        Delega a busca do repositório para o GitLabRepositoryProvider.
        O token não é mais necessário aqui, pois o provider já foi inicializado com ele.
        """
        print(f"[GitLab Conector] Delegando busca para GitLabRepositoryProvider...")
        # A lógica real está agora no provider, cumprindo o contrato da interface.
        return self.repository_provider.get_repository(repository_name=repositorio)
        
    # O método create_with_defaults pode ser removido se não for usado, 
    # ou mantido se for útil em algum lugar.
    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        provider = GitLabRepositoryProvider() 
        return cls(repository_provider=provider)
