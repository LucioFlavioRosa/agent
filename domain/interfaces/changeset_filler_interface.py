from abc import ABC, abstractmethod
from typing import Dict

class IChangesetFiller(ABC):
    """
    Interface para preenchimento/reconstituição de conjuntos de mudanças.
    Implementação obrigatória: ChangesetFiller em tools/preenchimento.py.
    """
    @abstractmethod
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        """
        Recebe o JSON agrupado e o inicial, retorna o conjunto de mudanças preenchido.
        """
        pass
