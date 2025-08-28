from abc import ABC, abstractmethod
from typing import Optional, Dict, List

class IUserTokenRepository(ABC):
    """
    Interface para repositório de associações entre usuários, grupos e tokens de repositório.
    
    Esta interface define o contrato para sistemas de armazenamento de associações
    usuário-grupo-token, permitindo diferentes implementações (Redis, banco de dados, etc.)
    e seguindo o princípio da segregação de interfaces.
    
    Modelo de Dados:
    - Usuários pertencem a grupos
    - Grupos têm tokens específicos por empresa/organização
    - Um token pode ser compartilhado por múltiplos usuários via grupo
    - Permite múltiplos tokens por empresa (diferentes grupos)
    
    Example:
        >>> repo = RedisUserTokenRepository()
        >>> repo.add_user_to_group("user123", "dev-team")
        >>> repo.set_group_token("dev-team", "myorg", "github-token-xyz")
        >>> token = repo.get_token_for_user("user123", "myorg")
    """
    
    @abstractmethod
    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """
        Associa um usuário a um grupo.
        
        Args:
            user_id (str): Identificador único do usuário
            group_id (str): Identificador único do grupo
            
        Returns:
            bool: True se a associação foi criada com sucesso, False caso contrário
            
        Raises:
            ValueError: Se user_id ou group_id forem inválidos
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        """
        pass
    
    @abstractmethod
    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """
        Remove a associação entre um usuário e um grupo.
        
        Args:
            user_id (str): Identificador único do usuário
            group_id (str): Identificador único do grupo
            
        Returns:
            bool: True se a associação foi removida com sucesso, False se não existia
            
        Raises:
            ValueError: Se user_id ou group_id forem inválidos
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        """
        pass
    
    @abstractmethod
    def set_group_token(self, group_id: str, empresa: str, token: str) -> bool:
        """
        Define o token de repositório para um grupo em uma empresa específica.
        
        Args:
            group_id (str): Identificador único do grupo
            empresa (str): Nome da empresa/organização (ex: "myorg", "acme-corp")
            token (str): Token de acesso ao repositório da empresa
            
        Returns:
            bool: True se o token foi definido com sucesso, False caso contrário
            
        Raises:
            ValueError: Se group_id, empresa ou token forem inválidos
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        
        Note:
            - Sobrescreve token existente se já houver um para o grupo+empresa
            - O mesmo grupo pode ter tokens diferentes para empresas diferentes
        """
        pass
    
    @abstractmethod
    def get_token_for_user(self, user_id: str, empresa: str) -> Optional[str]:
        """
        Obtém o token de repositório para um usuário em uma empresa específica.
        
        Este método realiza a consulta completa: usuário → grupos → token da empresa.
        Se o usuário pertencer a múltiplos grupos com tokens para a mesma empresa,
        retorna o primeiro encontrado (ordem de implementação específica).
        
        Args:
            user_id (str): Identificador único do usuário
            empresa (str): Nome da empresa/organização
            
        Returns:
            Optional[str]: Token de acesso se encontrado, None caso contrário
            
        Raises:
            ValueError: Se user_id ou empresa forem inválidos
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        
        Note:
            - Retorna None se usuário não pertencer a nenhum grupo
            - Retorna None se nenhum grupo do usuário tiver token para a empresa
            - Em caso de múltiplos tokens, a precedência depende da implementação
        """
        pass
    
    @abstractmethod
    def get_user_groups(self, user_id: str) -> List[str]:
        """
        Obtém a lista de grupos aos quais um usuário pertence.
        
        Args:
            user_id (str): Identificador único do usuário
            
        Returns:
            List[str]: Lista de identificadores de grupos. Lista vazia se usuário
                não pertencer a nenhum grupo
            
        Raises:
            ValueError: Se user_id for inválido
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        """
        pass
    
    @abstractmethod
    def get_group_tokens(self, group_id: str) -> Dict[str, str]:
        """
        Obtém todos os tokens de um grupo, organizados por empresa.
        
        Args:
            group_id (str): Identificador único do grupo
            
        Returns:
            Dict[str, str]: Dicionário mapeando empresa para token.
                Formato: {"empresa1": "token1", "empresa2": "token2"}
                Dicionário vazio se grupo não tiver tokens
            
        Raises:
            ValueError: Se group_id for inválido
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        """
        pass
    
    @abstractmethod
    def list_all_groups(self) -> List[str]:
        """
        Lista todos os grupos existentes no sistema.
        
        Returns:
            List[str]: Lista de identificadores de todos os grupos.
                Lista vazia se não houver grupos cadastrados
            
        Raises:
            ConnectionError: Se não conseguir conectar ao sistema de armazenamento
        
        Note:
            - Útil para operações administrativas e debugging
            - A ordem dos grupos depende da implementação específica
        """
        pass