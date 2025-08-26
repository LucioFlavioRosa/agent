from abc import ABC, abstractmethod
from typing import Optional

class ISecretManager(ABC):
    """
    Interface para gerenciamento de segredos.
    Abstrai a fonte de segredos (Azure Key Vault, AWS Secrets Manager, etc.)
    """
    @abstractmethod
    def get_secret(self, secret_name: str) -> str:
        """
        Obtém um segredo pelo nome.
        
        Args:
            secret_name: Nome do segredo a ser recuperado
            
        Returns:
            str: Valor do segredo
            
        Raises:
            ValueError: Se o segredo não for encontrado
        """
        pass
