from abc import ABC, abstractmethod
from typing import Dict, Any

class IChangesetFiller(ABC):
    @abstractmethod
    def main(self, json_agrupado: Dict[str, Any], json_inicial: Dict[str, Any]) -> Dict[str, Any]:
        pass