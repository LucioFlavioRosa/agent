from abc import ABC, abstractmethod
from typing import Dict

class IRepositoryReader(ABC):
    """
    Interface para leitores de repositório de código-fonte.
    """
    @abstractmethod
    def read_repository(self, nome_repo: str, tipo_analise: str, nome_branch: str = None) -> Dict[str, str]:
        """Lê os arquivos do repositório e retorna um dicionário {caminho: conteudo}."""
        pass
