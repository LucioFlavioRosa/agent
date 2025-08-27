from github import Repository
from typing import Dict
from domain.interfaces.secret_manager_interface import ISecretManager
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_secret_manager import AzureSecretManager
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubConnector:
    """
    Conector refatorado seguindo princípios SOLID para integração com repositórios.
    
    Esta classe orquestra a conexão com repositórios usando abstrações para
    gerenciamento de segredos e provedores de repositório. Implementa cache de
    conexões para otimizar performance e reduzir chamadas à API.
    
    IMPORTANTE: Esta classe agora é agnóstica ao provedor de repositório específico.
    Aceita qualquer implementação de IRepositoryProvider (GitHub, GitLab, Bitbucket, etc.)
    através de injeção de dependência, seguindo o mesmo padrão usado para LLMs.
    
    Responsabilidade única: gerenciar conexões com repositórios de forma eficiente
    e segura, abstraindo a complexidade de autenticação e cache.
    
    Attributes:
        _cached_repos (Dict[str, Repository]): Cache de repositórios conectados
        secret_manager (ISecretManager): Gerenciador de segredos injetado
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    
    Example:
        >>> # Uso com GitHub (padrão)
        >>> github_provider = GitHubRepositoryProvider()
        >>> connector = GitHubConnector(repository_provider=github_provider)
        >>> 
        >>> # Uso futuro com GitLab
        >>> # gitlab_provider = GitLabRepositoryProvider()
        >>> # connector = GitHubConnector(repository_provider=gitlab_provider)
    """
    _cached_repos: Dict[str, Repository] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        """
        Inicializa o conector com dependências injetadas.
        
        Args:
            repository_provider (IRepositoryProvider): Provedor de repositório a ser usado.
                Deve implementar IRepositoryProvider (ex: GitHubRepositoryProvider,
                GitLabRepositoryProvider, BitbucketRepositoryProvider)
            secret_manager (ISecretManager, optional): Gerenciador de segredos.
                Se None, usa AzureSecretManager como padrão
        
        Note:
            O repository_provider é obrigatório para garantir explicitamente qual
            provedor será usado, evitando dependências implícitas e facilitando testes.
        """
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
    
    def _get_token_for_org(self, org_name: str) -> str:
        """
        Obtém o token de autenticação para uma organização específica.
        
        Implementa fallback para token padrão caso não encontre token específico
        da organização, garantindo flexibilidade na configuração de tokens.
        
        Args:
            org_name (str): Nome da organização
            
        Returns:
            str: Token de autenticação válido para a organização
            
        Raises:
            ValueError: Se nenhum token válido for encontrado (nem específico nem padrão)
        """
        # Determina o prefixo do token baseado no tipo de provedor
        provider_type = type(self.repository_provider).__name__.lower()
        if 'github' in provider_type:
            token_prefix = 'github-token'
        elif 'gitlab' in provider_type:
            token_prefix = 'gitlab-token'
        elif 'bitbucket' in provider_type:
            token_prefix = 'bitbucket-token'
        else:
            token_prefix = 'repo-token'  # Fallback genérico
        
        token_secret_name = f"{token_prefix}-{org_name}"
        
        try:
            return self.secret_manager.get_secret(token_secret_name)
        except ValueError:
            print(f"AVISO: Segredo '{token_secret_name}' não encontrado. Tentando usar token padrão '{token_prefix}'.")
            try:
                return self.secret_manager.get_secret(token_prefix)
            except ValueError as e:
                raise ValueError(f"ERRO CRÍTICO: Nenhum token encontrado. Verifique se existe '{token_secret_name}' ou '{token_prefix}' no gerenciador de segredos.") from e
    
    def connection(self, repositorio: str) -> Repository:
        """
        Obtém um objeto de repositório, criando-o se necessário.
        
        Implementa cache para evitar reconexões desnecessárias e melhora
        a performance. Se o repositório não existir, tenta criá-lo automaticamente.
        
        Args:
            repositorio (str): Nome do repositório no formato 'org/repo'
            
        Returns:
            Repository: Objeto do repositório pronto para uso
            
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
            # Tenta obter o repositório existente usando o provedor injetado
            print(f"Tentando acessar o repositório '{repositorio}' via {type(self.repository_provider).__name__}...")
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
        Método de conveniência para criar uma instância com dependências padrão GitHub.
        
        Este método factory mantém compatibilidade com código existente que
        não precisa de injeção de dependência customizada. Por padrão, usa GitHub.
        
        Returns:
            GitHubConnector: Instância configurada com GitHubRepositoryProvider
                e AzureSecretManager como dependências padrão
        
        Note:
            Para usar outros provedores, instancie diretamente a classe:
            GitHubConnector(repository_provider=seu_provedor)
        """
        return cls(repository_provider=GitHubRepositoryProvider())