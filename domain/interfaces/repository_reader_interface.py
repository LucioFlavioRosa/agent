from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Union

class IRepositoryReader(ABC):
    @abstractmethod
    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str,
        repository_type: str,
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        pass
