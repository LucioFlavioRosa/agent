from abc import ABC, abstractmethod
from typing import Optional

class BaseFileReader(ABC):
    """
    Classe base para leitura de arquivos individuais de diferentes provedores.
    Facilita manutenção e reutilização, centralizando a interface de leitura.
    """
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider

    def read_single_file(self, repo_name, file_path: str, branch_name: Optional[str] = None, user_email: Optional[str] = None, group_resolver: Optional[object] = None) -> Optional[str]:
        """
        Método template para leitura de arquivo individual. Delegado para implementação específica.
        """
        return self._read_file_impl(repo_name, file_path, branch_name, user_email, group_resolver)

    @abstractmethod
    def _read_file_impl(self, repo_name, file_path: str, branch_name: Optional[str], user_email: Optional[str], group_resolver: Optional[object]) -> Optional[str]:
        """
        Implementação específica do provedor para leitura de arquivo.
        """
        pass
