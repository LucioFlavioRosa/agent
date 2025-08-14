from abc import ABC, abstractmethod
from typing import Dict

class IChangesetFiller(ABC):
    """
    Interface para preenchimento/reconstituição de conjuntos de mudanças.
    """
    @abstractmethod
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        pass
