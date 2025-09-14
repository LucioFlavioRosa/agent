import gitlab
import os
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager # Supondo que você use o Secret Manager

class GitLabRepositoryProvider(IRepositoryProvider):
    """
    Provider para interagir com repositórios GitLab.
    Responsável por gerenciar a conexão e autenticação.
    """
    def __init__(self):
        self.secret_manager = AzureSecretManager()
        self._gitlab_client = None

    def get_gitlab_client(self) -> gitlab.Gitlab:
        """
        Cria e retorna o cliente GitLab principal autenticado.
        Este é o método que estava faltando.
        """
        if self._gitlab_client:
            return self._gitlab_client

        try:
            # Busca a URL e o nome do segredo do token das variáveis de ambiente
            gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
            token_secret_name = os.getenv("GITLAB_TOKEN_SECRET_NAME")

            if not token_secret_name:
                raise ValueError("A variável de ambiente 'GITLAB_TOKEN_SECRET_NAME' não está definida.")

            # Busca o token real no Azure Key Vault
            gitlab_token = self.secret_manager.get_secret(token_secret_name)
            if not gitlab_token:
                raise ValueError(f"Não foi possível obter o segredo '{token_secret_name}' do Key Vault.")
            
            # Inicializa o cliente principal do GitLab e o armazena
            self._gitlab_client = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
            self._gitlab_client.auth() # Verifica se a autenticação foi bem-sucedida
            
            print("[GitLab Provider] Cliente GitLab autenticado com sucesso.")
            return self._gitlab_client

        except Exception as e:
            print(f"ERRO FATAL ao conectar com o GitLab: {e}")
            raise ConnectionError(f"Falha ao autenticar com o GitLab. Verifique a URL, o nome do segredo e as permissões. Erro: {e}") from e
    
    # Se você tiver outros métodos nesta classe, eles devem vir aqui.
    # Exemplo:
    def get_repository_type(self) -> str:
        return "gitlab"
