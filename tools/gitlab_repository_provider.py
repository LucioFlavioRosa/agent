import gitlab
from gitlab.v4.objects import Project
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from typing import Any

class GitLabRepositoryProvider(IRepositoryProvider):
    """
    Implementação do provedor de repositório para GitLab.
    Responsabilidade única: interagir com a API do GitLab.
    
    Esta classe implementa a interface IRepositoryProvider para GitLab,
    permitindo integração transparente com o sistema existente através
    de injeção de dependências, seguindo o mesmo padrão do GitHub.
    
    Características:
    - Suporte a projetos pessoais e de grupos
    - Criação automática de projetos quando necessário
    - Tratamento robusto de erros da API GitLab
    - Compatibilidade total com o sistema de conectores existente
    
    Example:
        >>> gitlab_provider = GitLabRepositoryProvider()
        >>> connector = GitHubConnector(repository_provider=gitlab_provider)
        >>> repo = connector.connection("grupo/projeto")
    """
    
    def get_repository(self, repository_name: str, token: str) -> Project:
        """
        Obtém um projeto existente do GitLab.
        
        Args:
            repository_name (str): Nome do repositório no formato 'grupo/projeto' ou 'usuario/projeto'
            token (str): Token de acesso pessoal do GitLab com permissões apropriadas
            
        Returns:
            Project: Objeto do projeto GitLab pronto para operações de commit e leitura
            
        Raises:
            ValueError: Se o projeto não for encontrado ou houver erro de acesso
        
        Note:
            - Suporta tanto projetos de grupos quanto pessoais
            - O token deve ter permissões de leitura no mínimo
            - Utiliza a API v4 do GitLab por padrão
        """
        try:
            # Inicializa cliente GitLab com token de autenticação
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            
            # Busca o projeto pelo nome completo (namespace/project)
            project = gl.projects.get(repository_name, lazy=True)
            
            # Verifica se o projeto existe fazendo uma chamada mínima
            _ = project.name  # Força carregamento dos dados básicos
            
            return project
            
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise ValueError(f"Projeto '{repository_name}' não encontrado no GitLab.")
            elif e.response_code == 403:
                raise ValueError(f"Acesso negado ao projeto '{repository_name}'. Verifique as permissões do token.")
            else:
                raise ValueError(f"Erro ao acessar projeto '{repository_name}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError:
            raise ValueError(f"Token de autenticação inválido para acessar '{repository_name}'.")
        except Exception as e:
            raise ValueError(f"Erro inesperado ao acessar projeto '{repository_name}': {e}") from e
    
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Project:
        """
        Cria um novo projeto no GitLab.
        
        Args:
            repository_name (str): Nome do repositório no formato 'namespace/projeto'
            token (str): Token de acesso pessoal com permissões de criação
            description (str, optional): Descrição do projeto. Defaults to ""
            private (bool, optional): Se o projeto deve ser privado. Defaults to True
            
        Returns:
            Project: Objeto do projeto GitLab criado
            
        Raises:
            ValueError: Se houver erro na criação ou formato inválido do nome
        
        Note:
            - Tenta criar no namespace especificado (grupo ou usuário)
            - Se o namespace for um grupo, o token deve ter permissões de criação no grupo
            - Projetos são inicializados com README por padrão
        """
        try:
            namespace_name, project_name_only = repository_name.split('/')
        except ValueError:
            raise ValueError(f"Nome do repositório '{repository_name}' tem formato inválido. Esperado 'namespace/projeto'.")
        
        try:
            # Inicializa cliente GitLab
            gl = gitlab.Gitlab(url="https://gitlab.com", private_token=token)
            
            # Configuração do projeto a ser criado
            project_data = {
                'name': project_name_only,
                'path': project_name_only,
                'description': description or "Projeto criado automaticamente pela plataforma de agentes de IA.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True,  # Facilita operações iniciais
                'default_branch': 'main'  # Padronização com convenções modernas
            }
            
            # Tenta determinar se é um grupo ou usuário pessoal
            try:
                # Primeiro tenta como grupo
                group = gl.groups.get(namespace_name, lazy=True)
                project_data['namespace_id'] = group.id
                project = gl.projects.create(project_data)
                
            except gitlab.exceptions.GitlabGetError:
                # Se não for grupo, cria no namespace do usuário atual
                # Remove namespace_id para criação no usuário atual
                if 'namespace_id' in project_data:
                    del project_data['namespace_id']
                project = gl.projects.create(project_data)
            
            return project
            
        except gitlab.exceptions.GitlabCreateError as e:
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{repository_name}' já existe no GitLab.")
            else:
                raise ValueError(f"Erro ao criar projeto '{repository_name}': {e}")
        except gitlab.exceptions.GitlabAuthenticationError:
            raise ValueError(f"Token de autenticação inválido para criar projeto '{repository_name}'.")
        except Exception as e:
            raise ValueError(f"Erro inesperado ao criar projeto '{repository_name}': {e}") from e