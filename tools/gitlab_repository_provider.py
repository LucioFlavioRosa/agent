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
    
    def create_repository(self, repository_name: str, token: str = None, description: str = "", private: bool = True) -> Project:
    """Cria um novo repositório GitLab, tratando namespaces de usuário e de grupo."""
        normalized_identifier = str(repository_name).strip()
        print(f"[GitLab Provider] Tentando criar repositório: {normalized_identifier}")
    
        try:
            namespace, project_name = self._parse_repository_name(normalized_identifier)
        except ValueError as e:
            raise ValueError(f"Nome de repositório inválido para criação: '{normalized_identifier}'. Use 'namespace/projeto'.") from e
    
        try:
            # Pega as informações do usuário autenticado pelo token
            user = self.client.user
            print(f"[GitLab Provider] Usuário autenticado: {user.username}")
            
            project_data = {
                'name': project_name,
                'path': project_name,
                'description': description or "Projeto criado automaticamente.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True
            }
    
            # --- LÓGICA CORRIGIDA ---
            # Compara o namespace desejado com o username do usuário do token
            if user.username.lower() != namespace.lower():
                # Se o namespace NÃO for o do usuário, busca o ID do GRUPO
                print(f"[GitLab Provider] Namespace '{namespace}' é um grupo. Buscando ID do grupo...")
                try:
                    group = self.client.groups.get(namespace)
                    project_data['namespace_id'] = group.id
                    print(f"[GitLab Provider] ID do grupo '{namespace}' encontrado: {group.id}")
                except gitlab.exceptions.GitlabGetError:
                     raise ValueError(f"O namespace '{namespace}' não foi encontrado como um grupo, e não é o seu namespace pessoal.")
            else:
                # Se o namespace é o do usuário, NÃO enviamos o namespace_id.
                # A API do GitLab usará o usuário autenticado como padrão.
                print(f"[GitLab Provider] Criando projeto no namespace pessoal de '{user.username}'.")
    
            # Cria o projeto com os dados corretos
            project = self.client.projects.create(project_data)
            print(f"[GitLab Provider] Projeto criado com sucesso: {project.web_url}")
            return project
            
        except gitlab.exceptions.GitlabCreateError as e:
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{normalized_identifier}' já existe.") from e
            raise ConnectionError(f"Erro ao criar projeto '{normalized_identifier}': {e}") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao criar projeto '{normalized_identifier}': {e}") from e
