from typing import Dict, Any
import os

class StepDependencyAnalyzer:
    """
    Funções auxiliares para analisar dependências entre passos do relatório.
    """
    @staticmethod
    def are_steps_dependent(step1: Dict[str, Any], step2: Dict[str, Any]) -> bool:
        """
        Considera dependentes se:
        - Modificam/criam o mesmo arquivo ou diretório
        - Um cria e outro modifica o mesmo arquivo/diretório
        - Estão na mesma camada e atuam sobre o mesmo recurso
        """
        path1 = (step1.get('caminho') or '').strip('`').lower()
        path2 = (step2.get('caminho') or '').strip('`').lower()
        # Se atuam no mesmo arquivo ou diretório
        if path1 and path2 and (path1 == path2 or os.path.commonpath([path1, path2]) == path1 or os.path.commonpath([path1, path2]) == path2):
            return True
        # Se um cria e outro modifica o mesmo arquivo
        acao1 = (step1.get('acao') or '').lower()
        acao2 = (step2.get('acao') or '').lower()
        if path1 == path2 and (('criar' in acao1 and 'modificar' in acao2) or ('criar' in acao2 and 'modificar' in acao1)):
            return True
        # Se estão na mesma camada e arquivo é vazio
        if not path1 and not path2 and step1.get('camada') == step2.get('camada'):
            return True
        return False
