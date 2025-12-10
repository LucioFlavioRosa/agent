from abc import ABC, abstractmethod
from typing import Any

class IRepositoryProvider(ABC):
    """
    Interface para provedores de repositório.
    Abstrai a implementação específica do provedor (GitHub, GitLab, etc.)
    """
    @abstractmethod
    def get_repository(self, repository_name: str, token: str) -> Any:
        """
        Obtém um objeto de repositório.
        
        Args:
            repository_name: Nome do repositório no formato 'org/repo'
            token: Token de autenticação
            
        Returns:
            Any: Objeto do repositório específico do provedor
        """
        pass
    
    @abstractmethod
    def create_repository(self, repository_name: str, token: str, description: str = "", private: bool = True) -> Any:
        """
        Cria um novo repositório.
        
        Args:
            repository_name: Nome do repositório no formato 'org/repo'
            token: Token de autenticação
            description: Descrição do repositório
            private: Se o repositório deve ser privado
            
        Returns:
            Any: Objeto do repositório criado
        """
        pass
