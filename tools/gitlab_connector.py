from gitlab import Project
from typing import Dict
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.gitlab_repository_provider import GitLabRepositoryProvider

class GitLabConnector:
    """
    Conector para integração com repositórios GitLab seguindo princípios SOLID.
    
    Esta classe orquestra a conexão com repositórios GitLab usando abstrações para
    gerenciamento de segredos e provedores de repositório. Implementa cache de
    conexões para otimizar performance e reduzir chamadas à API.
    
    Segue o mesmo padrão arquitetural do GitHubConnector, garantindo consistência
    na base de código e facilitando manutenção.
    
    Responsabilidade única: gerenciar conexões com repositórios GitLab de forma
    eficiente e segura, abstraindo a complexidade de autenticação e cache.
    
    Attributes:
        _cached_repos (Dict[str, Project]): Cache de repositórios conectados
        secret_manager (ISecretManager): Gerenciador de segredos injetado
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    
    Example:
        >>> gitlab_provider = GitLabRepositoryProvider()
        >>> connector = GitLabConnector(repository_provider=gitlab_provider)
        >>> repo = connector.connection("namespace/projeto")
    """
    _cached_repos: Dict[str, Project] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        """
        Inicializa o conector com dependências injetadas.
        
        Args:
            repository_provider (IRepositoryProvider): Provedor de repositório a ser usado.
                Deve implementar IRepositoryProvider (ex: GitLabRepositoryProvider)
            secret_manager (ISecretManager, optional): Gerenciador de segredos.
                Se None, usa AzureSecretManager como padrão
        
        Note:
            O repository_provider é obrigatório para garantir explicitamente qual
            provedor será usado, evitando dependências implícitas e facilitando testes.
        """
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_namespace(self, namespace_name: str) -> str:
        """
        Obtém o token de autenticação para um namespace específico do GitLab.
        
        Implementa fallback para token padrão caso não encontre token específico
        do namespace, garantindo flexibilidade na configuração de tokens.
        
        Args:
            namespace_name (str): Nome do namespace (grupo ou usuário)
            
        Returns:
            str: Token de autenticação válido para o namespace
            
        Raises:
            ValueError: Se nenhum token válido for encontrado (nem específico nem padrão)
        """
        # Token específico para o namespace
        token_secret_name = f"gitlab-token-{namespace_name}"
        
        try:
            return self.secret_manager.get_secret(token_secret_name)
        except ValueError:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Tentando usar token padrão 'gitlab-token'.")
            try:
                return self.secret_manager.get_secret("gitlab-token")
            except ValueError as e:
                raise ValueError(f"ERRO CRÍTICO: Nenhum token GitLab encontrado. Verifique se existe '{token_secret_name}' ou 'gitlab-token' no gerenciador de segredos.") from e
    
    def connection(self, repositorio: str) -> Project:
        """
        Obtém um objeto de projeto GitLab, criando-o se necessário.
        
        Implementa cache para evitar reconexões desnecessárias e melhora
        a performance. Se o repositório não existir, tenta criá-lo automaticamente.
        
        Args:
            repositorio (str): Nome do repositório no formato 'namespace/projeto'
            
        Returns:
            Project: Objeto do projeto GitLab pronto para uso
            
        Raises:
            ValueError: Se o formato do nome do repositório for inválido
                ou se não conseguir obter/criar o repositório
        """
        # Verifica cache primeiro para otimizar performance
        if repositorio in self._cached_repos:
            print(f"Retornando o objeto do projeto '{repositorio}' do cache.")
            return self._cached_repos[repositorio]
        
        # Valida formato do nome do repositório
        try:
            namespace_name, _ = repositorio.split('/', 1)
        except ValueError:
            raise ValueError(f"O nome do repositório '{repositorio}' tem formato inválido. Esperado 'namespace/projeto'.")
        
        # Obtém token de autenticação para o namespace
        token = self._get_token_for_namespace(namespace_name)
        
        try:
            # Tenta obter o repositório existente usando o provedor injetado
            print(f"Tentando acessar o projeto '{repositorio}' via {type(self.repository_provider).__name__}...")
            project = self.repository_provider.get_repository(repositorio, token)
            print(f"Projeto '{repositorio}' encontrado com sucesso.")
        except ValueError:
            # Se não encontrar, cria o repositório automaticamente
            print(f"AVISO: Projeto '{repositorio}' não encontrado. Tentando criá-lo...")
            project = self.repository_provider.create_repository(repositorio, token)
            print(f"SUCESSO: Projeto '{repositorio}' criado.")
        
        # Armazena no cache e retorna o projeto
        self._cached_repos[repositorio] = project
        return project
    
    @classmethod
    def create_with_defaults(cls) -> 'GitLabConnector':
        """
        Método de conveniência para criar uma instância com dependências padrão GitLab.
        
        Este método factory mantém compatibilidade com padrões de uso e
        facilita a criação de instâncias com configuração padrão.
        
        Returns:
            GitLabConnector: Instância configurada com GitLabRepositoryProvider
                e AzureSecretManager como dependências padrão
        
        Note:
            Para usar outros provedores, instancie diretamente a classe:
            GitLabConnector(repository_provider=seu_provedor)
        """
        return cls(repository_provider=GitLabRepositoryProvider())