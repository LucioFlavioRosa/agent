from github import Repository
from typing import Dict
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubConnector:
    """
    Conector refatorado seguindo princípios SOLID.
    Responsabilidade única: orquestrar a conexão com repositórios GitHub usando abstrações.
    """
    _cached_repos: Dict[str, Repository] = {}
    
    def __init__(self, secret_manager: ISecretManager = None, repository_provider: IRepositoryProvider = None):
        """
        Inicializa o conector com dependências injetadas.
        
        Args:
            secret_manager: Gerenciador de segredos (padrão: AzureSecretManager)
            repository_provider: Provedor de repositório (padrão: GitHubRepositoryProvider)
        """
        self.secret_manager = secret_manager or AzureSecretManager()
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
    
    def _get_token_for_org(self, org_name: str) -> str:
        """
        Obtém o token de autenticação para uma organização específica.
        
        Args:
            org_name: Nome da organização
            
        Returns:
            str: Token de autenticação
        """
        token_secret_name = f"github-token-{org_name}"
        
        try:
            return self.secret_manager.get_secret(token_secret_name)
        except ValueError:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Tentando usar token padrão 'github-token'.")
            try:
                return self.secret_manager.get_secret("github-token")
            except ValueError as e:
                raise ValueError(f"ERRO CRÍTICO: Nenhum token do GitHub encontrado. Verifique se existe '{token_secret_name}' ou 'github-token' no gerenciador de segredos.") from e
    
    def connection(self, repositorio: str) -> Repository:
        """
        Obtém um objeto de repositório, criando-o se necessário.
        
        Args:
            repositorio: Nome do repositório no formato 'org/repo'
            
        Returns:
            Repository: Objeto do repositório
        """
        if repositorio in self._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            return self._cached_repos[repositorio]
        
        try:
            org_name, _ = repositorio.split('/')
        except ValueError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")
        
        token = self._get_token_for_org(org_name)
        
        try:
            # Tenta obter o repositório existente
            print(f"Tentando acessar o repositório '{repositorio}'...")
            repo = self.repository_provider.get_repository(repositorio, token)
            print(f"Repositório '{repositorio}' encontrado com sucesso.")
        except ValueError:
            # Se não encontrar, cria o repositório
            print(f"AVISO: Repositório '{repositorio}' não encontrado. Tentando criá-lo...")
            repo = self.repository_provider.create_repository(repositorio, token)
            print(f"SUCESSO: Repositório '{repositorio}' criado.")
        
        # Cacheia e retorna o repositório
        self._cached_repos[repositorio] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConnector':
        """
        Método de conveniência para criar uma instância com dependências padrão.
        Mantém compatibilidade com código existente.
        
        Returns:
            GitHubConnector: Instância configurada com dependências padrão
        """
        return cls()
