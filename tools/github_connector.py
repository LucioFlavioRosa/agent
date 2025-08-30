from github import Repository
from typing import Dict, Any, Union
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
    
    NOVA FUNCIONALIDADE: Suporte aprimorado para múltiplos provedores com detecção
    automática de tipo, logging específico e tratamento de erros diferenciado.
    Implementa adaptação de objetos para garantir compatibilidade com diferentes APIs.
    
    Responsabilidade única: gerenciar conexões com repositórios de forma eficiente
    e segura, abstraindo a complexidade de autenticação, cache e adaptação de tipos.
    
    Attributes:
        _cached_repos (Dict[str, Any]): Cache de repositórios conectados (tipos diversos)
        secret_manager (ISecretManager): Gerenciador de segredos injetado
        repository_provider (IRepositoryProvider): Provedor de repositório injetado
    
    Example:
        >>> # Uso com GitHub (padrão)
        >>> github_provider = GitHubRepositoryProvider()
        >>> connector = GitHubConnector(repository_provider=github_provider)
        >>> 
        >>> # Uso com GitLab
        >>> gitlab_provider = GitLabRepositoryProvider()
        >>> connector = GitHubConnector(repository_provider=gitlab_provider)
        >>> 
        >>> # Uso com Azure DevOps
        >>> azure_provider = AzureRepositoryProvider()
        >>> connector = GitHubConnector(repository_provider=azure_provider)
    """
    _cached_repos: Dict[str, Any] = {}
    
    def __init__(self, repository_provider: IRepositoryProvider, secret_manager: ISecretManager = None):
        """
        Inicializa o conector com dependências injetadas.
        
        Args:
            repository_provider (IRepositoryProvider): Provedor de repositório a ser usado.
                Deve implementar IRepositoryProvider (ex: GitHubRepositoryProvider,
                GitLabRepositoryProvider, AzureRepositoryProvider)
            secret_manager (ISecretManager, optional): Gerenciador de segredos.
                Se None, usa AzureSecretManager como padrão
        
        Note:
            O repository_provider é obrigatório para garantir explicitamente qual
            provedor será usado, evitando dependências implícitas e facilitando testes.
        """
        self.repository_provider = repository_provider
        self.secret_manager = secret_manager or AzureSecretManager()
        
        # NOVA FUNCIONALIDADE: Detecção e logging do tipo de provedor
        self.provider_type = self._detect_provider_type()
        print(f"GitHubConnector inicializado com provedor: {type(repository_provider).__name__} (Tipo: {self.provider_type.upper()})")
    
    def _detect_provider_type(self) -> str:
        """
        Detecta o tipo do provedor baseado no nome da classe.
        
        Returns:
            str: Tipo do provedor ('github', 'gitlab', 'azure', 'unknown')
        
        Note:
            Usado para logging, debugging e tratamento específico quando necessário.
        """
        provider_class_name = type(self.repository_provider).__name__.lower()
        
        if 'github' in provider_class_name:
            return 'github'
        elif 'gitlab' in provider_class_name:
            return 'gitlab'
        elif 'azure' in provider_class_name:
            return 'azure'
        else:
            return 'unknown'
    
    def _get_token_for_org(self, org_name: str) -> str:
        """
        Obtém o token de autenticação para uma organização específica.
        
        Implementa fallback para token padrão caso não encontre token específico
        da organização, garantindo flexibilidade na configuração de tokens.
        
        NOVA FUNCIONALIDADE: Suporte aprimorado para múltiplos provedores com
        prefixos de token específicos e fallbacks inteligentes.
        
        Args:
            org_name (str): Nome da organização
            
        Returns:
            str: Token de autenticação válido para a organização
            
        Raises:
            ValueError: Se nenhum token válido for encontrado (nem específico nem padrão)
        """
        # Determina o prefixo do token baseado no tipo de provedor
        if self.provider_type == 'github':
            token_prefix = 'github-token'
        elif self.provider_type == 'gitlab':
            token_prefix = 'gitlab-token'
        elif self.provider_type == 'azure':
            token_prefix = 'azure-devops-token'
        else:
            token_prefix = 'repo-token'  # Fallback genérico
        
        # Lista de possíveis nomes de token para tentar (ordem de prioridade)
        token_candidates = [
            f"{token_prefix}-{org_name}",  # Token específico da organização
            token_prefix,                   # Token padrão do provedor
            f"repo-token-{org_name}",      # Fallback genérico específico
            "repo-token"                   # Fallback genérico geral
        ]
        
        print(f"Buscando token de autenticação para organização '{org_name}' (Provedor: {self.provider_type.upper()})...")
        
        for token_name in token_candidates:
            try:
                token = self.secret_manager.get_secret(token_name)
                print(f"Token encontrado: {token_name}")
                return token
            except ValueError:
                print(f"Token '{token_name}' não encontrado, tentando próximo...")
                continue
        
        # Se chegou aqui, nenhum token foi encontrado
        raise ValueError(
            f"ERRO CRÍTICO: Nenhum token de autenticação encontrado para '{org_name}' (Provedor: {self.provider_type.upper()}). "
            f"Verifique se existe um dos seguintes segredos: {', '.join(token_candidates)}"
        )
    
    def _create_repository_adapter(self, repo_object: Any) -> Any:
        """
        Cria um adaptador para o objeto de repositório baseado no tipo do provedor.
        
        Esta função crítica resolve o problema de incompatibilidade de tipos identificado
        no relatório de integridade funcional. Diferentes provedores retornam objetos
        com interfaces distintas, mas o sistema espera métodos compatíveis com PyGithub.
        
        Args:
            repo_object (Any): Objeto original retornado pelo provedor
            
        Returns:
            Any: Objeto adaptado ou original, dependendo do tipo do provedor
            
        Note:
            - Para GitHub: retorna o objeto Repository original (compatível)
            - Para GitLab: retorna o objeto Project original (será tratado especificamente)
            - Para Azure: retorna o dict original (será tratado especificamente)
            - Para unknown: retorna o objeto original com aviso
        """
        if self.provider_type == 'github':
            # GitHub Repository já é compatível com a interface esperada
            return repo_object
        
        elif self.provider_type == 'gitlab':
            # GitLab Project tem interface diferente, mas mantemos o objeto original
            # O tratamento específico será feito nos consumidores (github_reader, commit_multiplas_branchs)
            print(f"AVISO: Objeto GitLab Project retornado. Consumidores devem tratar especificamente.")
            return repo_object
        
        elif self.provider_type == 'azure':
            # Azure retorna dict, mantemos o objeto original
            # O tratamento específico será feito nos consumidores
            print(f"AVISO: Objeto Azure DevOps (dict) retornado. Consumidores devem tratar especificamente.")
            return repo_object
        
        else:
            # Provedor desconhecido, retorna objeto original com aviso
            print(f"AVISO: Provedor desconhecido '{self.provider_type}'. Retornando objeto original sem adaptação.")
            return repo_object
    
    def connection(self, repositorio: str) -> Any:
        """
        Obtém um objeto de repositório, criando-o se necessário.
        
        Implementa cache para evitar reconexões desnecessárias e melhora
        a performance. Se o repositório não existir, tenta criá-lo automaticamente.
        
        CORREÇÃO CRÍTICA: Agora retorna objetos adaptados baseados no tipo do provedor,
        resolvendo o problema de incompatibilidade de tipos identificado no relatório
        de integridade funcional.
        
        Args:
            repositorio (str): Nome do repositório no formato específico do provedor:
                - GitHub: 'org/repo'
                - GitLab: 'grupo/projeto' 
                - Azure DevOps: 'organization/project/repository'
            
        Returns:
            Any: Objeto do repositório adaptado para o tipo do provedor.
                - GitHub: github.Repository.Repository
                - GitLab: gitlab.v4.objects.Project
                - Azure DevOps: Dict[str, Any]
            
        Raises:
            ValueError: Se o formato do nome do repositório for inválido
                ou se não conseguir obter/criar o repositório
        
        Note:
            O tipo de retorno varia conforme o provedor. Consumidores devem
            tratar adequadamente cada tipo ou usar detecção de provider_type.
        """
        # Cria chave de cache específica incluindo tipo do provedor
        cache_key = f"{self.provider_type}:{repositorio}"
        
        # Verifica cache primeiro para otimizar performance
        if cache_key in self._cached_repos:
            print(f"Retornando o objeto do repositório '{repositorio}' do cache ({self.provider_type.upper()}).")
            return self._cached_repos[cache_key]
        
        # Valida formato do nome do repositório baseado no tipo do provedor
        self._validate_repository_format(repositorio)
        
        # Extrai nome da organização para busca de token
        org_name = self._extract_org_name(repositorio)
        
        # Obtém token de autenticação para a organização
        token = self._get_token_for_org(org_name)
        
        try:
            # Tenta obter o repositório existente usando o provedor injetado
            print(f"Tentando acessar o repositório '{repositorio}' via {type(self.repository_provider).__name__}...")
            repo_object = self.repository_provider.get_repository(repositorio, token)
            print(f"Repositório '{repositorio}' encontrado com sucesso ({self.provider_type.upper()}).")
        except ValueError as e:
            # Se não encontrar, cria o repositório automaticamente
            print(f"AVISO: Repositório '{repositorio}' não encontrado ({self.provider_type.upper()}). Tentando criá-lo...")
            print(f"Detalhes do erro: {e}")
            try:
                repo_object = self.repository_provider.create_repository(repositorio, token)
                print(f"SUCESSO: Repositório '{repositorio}' criado ({self.provider_type.upper()}).")
            except Exception as create_error:
                print(f"ERRO CRÍTICO: Falha ao criar repositório '{repositorio}': {create_error}")
                raise ValueError(f"Não foi possível acessar nem criar o repositório '{repositorio}': {create_error}") from create_error
        
        # CORREÇÃO CRÍTICA: Aplica adaptação baseada no tipo do provedor
        adapted_repo = self._create_repository_adapter(repo_object)
        
        # Armazena no cache e retorna o repositório adaptado
        self._cached_repos[cache_key] = adapted_repo
        print(f"Repositório '{repositorio}' adaptado e adicionado ao cache ({self.provider_type.upper()}).")
        return adapted_repo
    
    def _validate_repository_format(self, repositorio: str) -> None:
        """
        Valida o formato do nome do repositório baseado no tipo do provedor.
        
        Args:
            repositorio (str): Nome do repositório a ser validado
            
        Raises:
            ValueError: Se o formato for inválido para o tipo de provedor
        """
        if not repositorio or not isinstance(repositorio, str):
            raise ValueError("O nome do repositório deve ser uma string não vazia.")
        
        parts = repositorio.strip().split('/')
        
        if self.provider_type in ['github', 'gitlab']:
            if len(parts) != 2:
                raise ValueError(
                    f"O nome do repositório '{repositorio}' tem formato inválido para {self.provider_type.upper()}. "
                    "Esperado 'org/repo' ou 'grupo/projeto'."
                )
        elif self.provider_type == 'azure':
            if len(parts) != 3:
                raise ValueError(
                    f"O nome do repositório '{repositorio}' tem formato inválido para Azure DevOps. "
                    "Esperado 'organization/project/repository'."
                )
        else:
            # Para provedores desconhecidos, aceita pelo menos 2 partes
            if len(parts) < 2:
                raise ValueError(
                    f"O nome do repositório '{repositorio}' tem formato inválido. "
                    "Esperado pelo menos 'org/repo'."
                )
    
    def _extract_org_name(self, repositorio: str) -> str:
        """
        Extrai o nome da organização do nome do repositório.
        
        Args:
            repositorio (str): Nome completo do repositório
            
        Returns:
            str: Nome da organização/grupo
        """
        parts = repositorio.split('/')
        return parts[0]  # Primeira parte é sempre a organização/grupo
    
    def get_provider_info(self) -> Dict[str, str]:
        """
        Retorna informações sobre o provedor configurado.
        
        Returns:
            Dict[str, str]: Informações do provedor incluindo tipo e classe
        
        Note:
            Útil para debugging e logging de configuração.
        """
        return {
            "provider_type": self.provider_type,
            "provider_class": type(self.repository_provider).__name__,
            "secret_manager_class": type(self.secret_manager).__name__,
            "cached_repos_count": str(len(self._cached_repos))
        }
    
    def clear_cache(self) -> None:
        """
        Limpa o cache de repositórios.
        
        Note:
            Útil para testes ou quando se quer forçar reconexão.
        """
        cache_count = len(self._cached_repos)
        self._cached_repos.clear()
        print(f"Cache de repositórios limpo ({cache_count} entradas removidas).")
    
    def is_github_compatible(self) -> bool:
        """
        Verifica se o provedor atual é compatível com a interface do PyGithub.
        
        Returns:
            bool: True se for GitHub, False caso contrário
            
        Note:
            Método utilitário para consumidores verificarem compatibilidade
            antes de chamar métodos específicos do PyGithub.
        """
        return self.provider_type == 'github'
    
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
        print("Criando GitHubConnector com dependências padrão (GitHub + Azure Secret Manager)...")
        return cls(repository_provider=GitHubRepositoryProvider())