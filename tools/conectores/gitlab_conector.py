import gitlab
from typing import Dict, Union, Any
from .base_conector import BaseConector
from tools.gitlab_repository_provider import GitLabRepositoryProvider

class GitLabConector(BaseConector):
    """
    Conector para interagir com o GitLab.
    Gerencia a conexão e as operações de busca e criação de projetos.
    """
    def __init__(self, repository_provider: GitLabRepositoryProvider):
        """
        Inicializa o conector.
        A conexão principal com o GitLab é estabelecida aqui e armazenada
        em self.client para ser usada por todos os outros métodos.
        """
        super().__init__(repository_provider=repository_provider)
        # Assumimos que o seu provider tem um método para retornar o cliente gitlab principal
        # autenticado. Se o nome do método for diferente, ajuste aqui.
        self.client: gitlab.Gitlab = self.repository_provider.get_gitlab_client() 
        if not isinstance(self.client, gitlab.Gitlab):
             raise TypeError("repository_provider.get_gitlab_client() não retornou um objeto gitlab.Gitlab válido.")

    def connection(self, repositorio: str) -> Union[object]:
        """
        Ponto de entrada principal. Obtém um objeto de projeto do GitLab
        seja por ID ou por caminho (path).
        """
        normalized_repo = self._normalize_repository_identifier(repositorio)
        
        try:
            # A conexão (self.client) já foi estabelecida no __init__.
            # Agora apenas decidimos qual método de busca usar.
            if self._is_gitlab_project_id(normalized_repo):
                return self._get_project_by_id(normalized_repo)
            else:
                return self._get_project_by_path(normalized_repo)
                
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Erro fatal ao conectar com repositório GitLab '{normalized_repo}': {e}"
            ) from e

    def _get_project_by_id(self, project_id: str) -> object:
        """Busca um projeto GitLab pelo seu ID numérico."""
        try:
            print(f"[GitLab Conector] Buscando projeto por ID: {project_id}")
            # CORREÇÃO: Usa self.client, que é o cliente GitLab principal
            project = self.client.projects.get(project_id)
            print(f"[GitLab Conector] Projeto encontrado: {project.path_with_namespace} (ID: {project.id})")
            return project
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise ValueError(
                    f"Projeto GitLab com ID '{project_id}' não encontrado ou acesso negado."
                ) from e
            else:
                raise ValueError(
                    f"Erro inesperado ao acessar projeto ID '{project_id}': {e}"
                ) from e

    def _get_project_by_path(self, repositorio_path: str) -> object:
        """Busca um projeto GitLab pelo seu caminho (ex: 'namespace/projeto')."""
        try:
            print(f"[GitLab Conector] Buscando projeto por caminho: {repositorio_path}")
            # CORREÇÃO: Usa self.client, que é o cliente GitLab principal
            project = self.client.projects.get(repositorio_path)
            print(f"[GitLab Conector] Projeto encontrado: {project.path_with_namespace} (ID: {project.id})")
            return project
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                print(f"[GitLab Conector] Projeto '{repositorio_path}' não encontrado. Tentando criar...")
                # CORREÇÃO: A chamada para criar o projeto não precisa mais do cliente como parâmetro
                return self._create_project_by_path(repositorio_path)
            else:
                raise ValueError(
                    f"Erro inesperado ao acessar projeto '{repositorio_path}': {e}"
                ) from e
    
    def _create_project_by_path(self, repositorio_path: str) -> object:
        """Cria um novo projeto no GitLab se ele não for encontrado."""
        parts = repositorio_path.split('/')
        if len(parts) < 2:
            raise ValueError(f"Formato de repositório inválido para criação: '{repositorio_path}'. Use 'namespace/projeto'.")
        
        namespace = parts[0]
        project_name = parts[-1]
        
        print(f"[GitLab Conector] Tentando criar projeto '{project_name}' no namespace '{namespace}'...")
        
        # CORREÇÃO: Usa o self.client que já está autenticado
        namespace_info = self._check_namespace_exists(namespace)
        
        if not namespace_info['exists']:
            raise ValueError(f"O namespace '{namespace}' não foi encontrado como um grupo ou usuário no GitLab.")
        
        try:
            project_data = {'name': project_name, 'path': project_name, 'visibility': 'private'}
            
            if namespace_info['type'] == 'group':
                project_data['namespace_id'] = namespace_info['id']
            else: # tipo 'user'
                if self.client.user.username != namespace:
                    raise ValueError(f"Não é possível criar projeto no namespace de outro usuário ('{namespace}'). O token pertence a '{self.client.user.username}'.")

            # CORREÇÃO: Usa self.client para criar o projeto
            created_project = self.client.projects.create(project_data)
            print(f"[GitLab Conector] Projeto '{repositorio_path}' criado com sucesso! ID: {created_project.id}")
            return created_project
            
        except Exception as create_error:
            # Trata o caso de o projeto já existir (corrida de concorrência)
            if "already exists" in str(create_error).lower():
                print(f"[GitLab Conector] Projeto '{repositorio_path}' já existe. Tentando acessá-lo novamente...")
                try:
                    # CORREÇÃO: Usa self.client para buscar o projeto
                    return self.client.projects.get(repositorio_path)
                except Exception as get_error:
                    raise ValueError(f"Projeto '{repositorio_path}' existe mas não pode ser acessado: {get_error}") from get_error
            else:
                raise ValueError(f"Erro inesperado ao criar projeto '{repositorio_path}': {create_error}") from create_error

    def _is_gitlab_project_id(self, repositorio: str) -> bool:
        """Verifica se o identificador do repositório é um ID numérico."""
        try:
            int(repositorio)
            return True
        except ValueError:
            return False

    def _normalize_repository_identifier(self, repositorio: str) -> str:
        """Remove espaços em branco do identificador."""
        return repositorio.strip()

    def _check_namespace_exists(self, namespace: str) -> Dict[str, Any]:
        """Verifica se um namespace existe como usuário ou grupo."""
        try:
            # CORREÇÃO: Usa self.client
            user = self.client.users.list(username=namespace)
            if user:
                return {'exists': True, 'type': 'user', 'id': user[0].id}

            group = self.client.groups.get(namespace)
            if group:
                return {'exists': True, 'type': 'group', 'id': group.id}
            
            return {'exists': False, 'type': None, 'id': None}
        except Exception:
            return {'exists': False, 'type': None, 'id': None}

    @classmethod
    def create_with_defaults(cls) -> 'GitLabConector':
        """Método de fábrica para criar uma instância com configurações padrão."""
        # Assume que o GitLabRepositoryProvider sabe como se autenticar
        # para que o get_gitlab_client() funcione.
        provider = GitLabRepositoryProvider() 
        return cls(repository_provider=provider)
