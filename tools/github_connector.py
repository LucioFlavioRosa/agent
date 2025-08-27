from github import Repository
from typing import Dict
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubConnector:
    """
    Conector refatorado seguindo princípios SOLID para integração com GitHub.
    
    Esta classe orquestra a conexão com repositórios GitHub usando abstrações
    para gerenciamento de segredos e provedores de repositório. Implementa
    cache de conexões para otimizar performance e reduzir chamadas à API.
    
    Responsabilidade única: gerenciar conexões com repositórios GitHub de forma
    eficiente e segura, abstraindo a complexidade de autenticação e cache.
    
    Attributes:
        _cached_repos (Dict[str, Repository]): Cache de repositórios conectados
        secret_manager (ISecretManager): Gerenciador de segredos injetado
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    """
    _cached_repos: Dict[str, Repository] = {}
    
    def __init__(self, secret_manager: ISecretManager = None, repository_provider: IRepositoryProvider = None):
        """
        Inicializa o conector com dependências injetadas.
        
        Args:
            secret_manager (ISecretManager, optional): Gerenciador de segredos.
                Se None, usa AzureSecretManager como padrão
            repository_provider (IRepositoryProvider, optional): Provedor de repositório.
                Se None, usa GitHubRepositoryProvider como padrão
        """
        self.secret_manager = secret_manager or AzureSecretManager()
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
    
    def _get_token_for_org(self, org_name: str) -> str:
        """
        Obtém o token de autenticação para uma organização específica.
        
        Implementa fallback para token padrão caso não encontre token específico
        da organização, garantindo flexibilidade na configuração de tokens.
        
        Args:
            org_name (str): Nome da organização GitHub
            
        Returns:
            str: Token de autenticação válido para a organização
            
        Raises:
            ValueError: Se nenhum token válido for encontrado (nem específico nem padrão)
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
        
        Implementa cache para evitar reconexões desnecessárias e melhora
        a performance. Se o repositório não existir, tenta criá-lo automaticamente.
        
        Args:
            repositorio (str): Nome do repositório no formato 'org/repo'
            
        Returns:
            Repository: Objeto do repositório GitHub pronto para uso
            
        Raises:
            ValueError: Se o formato do nome do repositório for inválido
                ou se não conseguir obter/criar o repositório
        """
        # Verifica cache primeiro para otimizar performance
        if repositorio in self._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache.")
            return self._cached_repos[repositorio]
        
        # Valida formato do nome do repositório
        try:
            org_name, _ = repositorio.split('/')
        except ValueError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'organizacao/repositorio'.")
        
        # Obtém token de autenticação para a organização
        token = self._get_token_for_org(org_name)
        
        try:
            # Tenta obter o repositório existente
            print(f"Tentando acessar o repositório '{repositorio}'...")
            repo = self.repository_provider.get_repository(repositorio, token)
            print(f"Repositório '{repositorio}' encontrado com sucesso.")
        except ValueError:
            # Se não encontrar, cria o repositório automaticamente
            print(f"AVISO: Repositório '{repositorio}' não encontrado. Tentando criá-lo...")
            repo = self.repository_provider.create_repository(repositorio, token)
            print(f"SUCESSO: Repositório '{repositorio}' criado.")
        
        # Armazena no cache e retorna o repositório
        self._cached_repos[repositorio] = repo
        return repo
    
    @classmethod
    def create_with_defaults(cls) -> 'GitHubConnector':
        """
        Método de conveniência para criar uma instância com dependências padrão.
        
        Este método factory mantém compatibilidade com código existente que
        não precisa de injeção de dependência customizada.
        
        Returns:
            GitHubConnector: Instância configurada com dependências padrão
                (AzureSecretManager e GitHubRepositoryProvider)
        """
        return cls()