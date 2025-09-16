from domain.interfaces.repository_provider_interface import IRepositoryProvider
from domain.interfaces.secret_manager_interface import ISecretManager
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider

class RepositoryProviderFactory:
    """
    Fábrica responsável por criar a instância correta do provedor de repositório
    com o token de autenticação apropriado.
    """
    def __init__(self, secret_manager: ISecretManager):
        """A fábrica precisa do secret manager para poder buscar os tokens."""
        self.secret_manager = secret_manager

    def create_provider(self, repository_type: str, repo_name: str) -> IRepositoryProvider:
        """
        Cria e retorna uma instância do provedor de repositório correto
        com o token apropriado para a organização/usuário.
        """
        if not repository_type or not repo_name:
            raise ValueError("repository_type e repo_name são obrigatórios.")

        print(f"[Factory] Criando provider para tipo '{repository_type}' e repo '{repo_name}'")

        # 1. Extrai a organização/dono do nome do repositório para buscar o token certo
        #    Ex: "aisrosa/meu-projeto" -> "aisrosa"
        try:
            org_name = repo_name.split('/')[0]
        except IndexError:
            raise ValueError(f"Formato de repo_name inválido: '{repo_name}'. Esperado 'dono/projeto'.")

        # 2. Lógica para determinar o nome do segredo do token dinamicamente
        #    Ex: "github-token-aisrosa", "gitlab-token-meu-grupo"
        token_secret_name = f"{repository_type}-token-{org_name}"
        
        try:
            print(f"[Factory] Buscando segredo do token no Key Vault: '{token_secret_name}'")
            token = self.secret_manager.get_secret(token_secret_name)
            if not token:
                raise ValueError("Token não encontrado no Key Vault para o segredo especificado.")
        except Exception as e:
            raise ConnectionError(
                f"Falha ao obter o token '{token_secret_name}' para '{org_name}'. "
                f"Verifique se o segredo existe no Key Vault e se a aplicação tem permissão. Erro: {e}"
            ) from e

        # 3. Com o token dinâmico em mãos, cria a instância correta do provider
        provider_type_lower = repository_type.lower().strip()
        
        if provider_type_lower == 'github':
            return GitHubRepositoryProvider(token=token)
        elif provider_type_lower == 'gitlab':
            return GitLabRepositoryProvider(token=token)
        elif provider_type_lower in ['azure', 'azure_devops']:
            return AzureRepositoryProvider(token=token)
        else:
            raise ValueError(f"Tipo de repositório desconhecido: '{repository_type}'")
