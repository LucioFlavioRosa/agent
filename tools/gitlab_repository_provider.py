import gitlab
import os
from gitlab.v4.objects import Project
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager # Supondo que você use o Secret Manager

class GitLabRepositoryProvider(IRepositoryProvider):
    """
    Provider que implementa a lógica de negócio para interagir com repositórios GitLab.
    """
    def __init__(self):
        self.secret_manager = AzureSecretManager()
        self.client = self._initialize_client()

    def _initialize_client(self) -> gitlab.Gitlab:
        """Inicializa e autentica o cliente GitLab principal."""
        try:
            gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
            token_secret_name = os.getenv("GITLAB_TOKEN_SECRET_NAME")
            if not token_secret_name:
                raise ValueError("Variável de ambiente 'GITLAB_TOKEN_SECRET_NAME' não definida.")

            gitlab_token = self.secret_manager.get_secret(token_secret_name)
            if not gitlab_token:
                raise ValueError(f"Não foi possível obter o segredo '{token_secret_name}' do Key Vault.")
            
            gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
            gl.auth()
            print("[GitLab Provider] Cliente GitLab autenticado com sucesso.")
            return gl
        except Exception as e:
            raise ConnectionError(f"Falha ao autenticar com o GitLab: {e}") from e

    # --- IMPLEMENTAÇÃO DOS MÉTODOS OBRIGATÓRIOS DA INTERFACE ---

    def get_repository(self, repository_name: str, token: str = None) -> Project:
        """Obtém um objeto de repositório GitLab por ID ou caminho."""
        normalized_identifier = str(repository_name).strip()
        print(f"[GitLab Provider] Buscando projeto: '{normalized_identifier}'")
        try:
            project = self.client.projects.get(normalized_identifier)
            print(f"[GitLab Provider] Projeto encontrado: '{project.name_with_namespace}' (ID: {project.id}).")
            return project
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise ValueError(f"Repositório GitLab '{normalized_identifier}' não encontrado ou acesso negado.") from e
            raise ConnectionError(f"Erro da API GitLab ({e.response_code}) ao buscar '{normalized_identifier}': {e}") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao buscar projeto '{normalized_identifier}': {e}") from e

    def create_repository(self, repository_name: str, token: str = None, description: str = "", private: bool = True) -> Project:
        """Cria um novo repositório GitLab."""
        normalized_identifier = str(repository_name).strip()
        print(f"[GitLab Provider] Tentando criar repositório: {normalized_identifier}")
        
        try:
            namespace, project_name = self._parse_repository_name(normalized_identifier)
        except ValueError as e:
            raise ValueError(f"Nome de repositório inválido para criação: '{normalized_identifier}'. Use 'namespace/projeto'.") from e

        try:
            namespace_id = self._get_namespace_id(namespace)
            
            project_data = {
                'name': project_name,
                'path': project_name,
                'namespace_id': namespace_id,
                'description': description or "Projeto criado automaticamente.",
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True
            }
            
            project = self.client.projects.create(project_data)
            print(f"[GitLab Provider] Projeto criado com sucesso: {project.web_url}")
            return project
        except gitlab.exceptions.GitlabCreateError as e:
            if "has already been taken" in str(e):
                raise ValueError(f"Projeto '{normalized_identifier}' já existe.") from e
            raise ConnectionError(f"Erro ao criar projeto '{normalized_identifier}': {e}") from e
        except Exception as e:
            raise RuntimeError(f"Erro inesperado ao criar projeto '{normalized_identifier}': {e}") from e

    # --- MÉTODOS AUXILIARES ---

    def _get_namespace_id(self, namespace: str) -> int:
        """Busca o ID de um namespace (grupo ou usuário)."""
        try:
            group = self.client.groups.get(namespace)
            return group.id
        except gitlab.exceptions.GitlabGetError:
            try:
                user = self.client.users.list(username=namespace)[0]
                return user.id
            except (gitlab.exceptions.GitlabGetError, IndexError):
                raise ValueError(f"Namespace '{namespace}' não encontrado como grupo ou usuário.")

    def _parse_repository_name(self, repository_name: str) -> tuple[str, str]:
        """Divide 'namespace/projeto' em uma tupla."""
        parts = repository_name.split('/')
        if len(parts) < 2:
            raise ValueError("Formato inválido.")
        return ('/'.join(parts[:-1]), parts[-1])
