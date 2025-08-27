from gitlab import Gitlab, Project
from gitlab.exceptions import GitlabGetError, GitlabCreateError
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from typing import Any

class GitLabRepositoryProvider(IRepositoryProvider):
    """
    Implementação do provedor de repositório para GitLab.
    Responsabilidade única: interagir com a API do GitLab.
    
    Esta classe implementa a interface IRepositoryProvider para GitLab,
    permitindo acesso e criação de repositórios usando a API do GitLab.
    Segue o mesmo padrão arquitetural do GitHubRepositoryProvider.
    """
    
    def get_repository(self, repository_name: str, token: str) -> Project:
        """
        Obtém um repositório existente do GitLab.
        
        Args:
            repository_name: Nome do repositório no formato 'org/repo' ou 'user/repo'
            token: Token de autenticação do GitLab (Personal Access Token)
            
        Returns:
            Project: Objeto do projeto do GitLab
            
        Raises:
            ValueError: Se o repositório não for encontrado ou houver erro de acesso
        """
        try:
            # Conecta ao GitLab usando o token fornecido
            gl = Gitlab(url="https://gitlab.com", private_token=token)
            
            # Obtém o projeto usando o nome completo (namespace/project)
            project = gl.projects.get(repository_name)
            return project
            
        except GitlabGetError as e:
            if e.response_code == 404:
                raise ValueError(f"Repositório '{repository_name}' não encontrado no GitLab.")
            else:
                raise ValueError(f"Erro ao acessar repositório '{repository_name}': {e.error_message}") from e
        except Exception as e:
            raise ValueError(f"Erro inesperado ao acessar repositório '{repository_name}': {e}") from e
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Project:
        """
        Cria um novo repositório no GitLab.
        
        Args:
            repository_name: Nome do repositório no formato 'org/repo' ou 'user/repo'
            token: Token de autenticação do GitLab
            description: Descrição do repositório
            private: Se o repositório deve ser privado (visibility_level)
            
        Returns:
            Project: Objeto do projeto criado no GitLab
            
        Raises:
            ValueError: Se houver erro na criação do repositório
        """
        try:
            # Separa namespace e nome do projeto
            if '/' in repository_name:
                namespace_name, project_name = repository_name.split('/', 1)
            else:
                # Se não há namespace, usa o usuário atual
                namespace_name = None
                project_name = repository_name
        except ValueError:
            raise ValueError(f"Nome do repositório '{repository_name}' tem formato inválido. Esperado 'namespace/projeto' ou 'projeto'.")
        
        try:
            gl = Gitlab(url="https://gitlab.com", private_token=token)
            
            # Configura parâmetros do projeto
            project_data = {
                'name': project_name,
                'description': description or "Repositório criado automaticamente pela plataforma de agentes de IA.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True
            }
            
            # Se há namespace específico, tenta criar no namespace
            if namespace_name:
                try:
                    # Busca o namespace (grupo ou usuário)
                    namespaces = gl.namespaces.list(search=namespace_name)
                    if namespaces:
                        project_data['namespace_id'] = namespaces[0].id
                    else:
                        # Se namespace não encontrado, cria no usuário atual
                        print(f"AVISO: Namespace '{namespace_name}' não encontrado. Criando no usuário atual.")
                except Exception as e:
                    print(f"AVISO: Erro ao buscar namespace '{namespace_name}': {e}. Criando no usuário atual.")
            
            # Cria o projeto
            project = gl.projects.create(project_data)
            return project
            
        except GitlabCreateError as e:
            raise ValueError(f"Erro ao criar repositório '{repository_name}': {e.error_message}") from e
        except Exception as e:
            raise ValueError(f"Erro inesperado ao criar repositório '{repository_name}': {e}") from e