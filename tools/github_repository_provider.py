from github import Github, Repository, Auth, UnknownObjectException, GithubException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from typing import Any

class GitHubRepositoryProvider(IRepositoryProvider):
    """
    Implementação do provedor de repositório para GitHub.
    Responsabilidade única: interagir com a API do GitHub.
    """
    
    def get_repository(self, repository_name: str, token: str) -> Repository:
        """
        Obtém um repositório existente do GitHub.
        
        Args:
            repository_name: Nome do repositório no formato 'org/repo'
            token: Token de autenticação do GitHub
            
        Returns:
            Repository: Objeto do repositório do GitHub
            
        Raises:
            ValueError: Se o repositório não for encontrado
        """
        try:
            auth = Auth.Token(token)
            github_client = Github(auth=auth)
            return github_client.get_repo(repository_name)
        except UnknownObjectException:
            raise ValueError(f"Repositório '{repository_name}' não encontrado no GitHub.")
        except Exception as e:
            raise ValueError(f"Erro ao acessar repositório '{repository_name}': {e}") from e
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Repository:
        """
        Cria um novo repositório no GitHub.
        
        Args:
            repository_name: Nome do repositório no formato 'org/repo'
            token: Token de autenticação do GitHub
            description: Descrição do repositório
            private: Se o repositório deve ser privado
            
        Returns:
            Repository: Objeto do repositório criado
        """
        try:
            org_name, repo_name_only = repository_name.split('/')
        except ValueError:
            raise ValueError(f"Nome do repositório '{repository_name}' tem formato inválido. Esperado 'org/repo'.")
        
        try:
            auth = Auth.Token(token)
            github_client = Github(auth=auth)
            
            # Tenta criar na organização primeiro
            try:
                org = github_client.get_organization(org_name)
                return org.create_repo(
                    name=repo_name_only,
                    description=description or "Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=private,
                    auto_init=True
                )
            except UnknownObjectException:
                # Se não for uma organização, cria na conta do usuário
                user = github_client.get_user()
                return user.create_repo(
                    name=repo_name_only,
                    description=description or "Repositório criado automaticamente pela plataforma de agentes de IA.",
                    private=private,
                    auto_init=True
                )
        except Exception as e:
            raise ValueError(f"Erro ao criar repositório '{repository_name}': {e}") from e
