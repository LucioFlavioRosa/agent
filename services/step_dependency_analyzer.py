from typing import Dict

class StepDependencyAnalyzer:
    """
    Utilitário para análise de dependências entre passos de relatório de implementação.
    """
    @staticmethod
    def are_steps_dependent(step1: Dict, step2: Dict) -> bool:
        """
        Verifica se dois passos são dependentes.
        Dependência ocorre se:
        - Modificam/criam o mesmo arquivo ou diretório
        - Um cria/modifica e o outro modifica o mesmo caminho
        """
        path1 = StepDependencyAnalyzer._normalize_path(step1.get('Caminho do Arquivo', ''))
        path2 = StepDependencyAnalyzer._normalize_path(step2.get('Caminho do Arquivo', ''))
        if not path1 or not path2:
            return False
        # Dependência se o caminho é exatamente igual
        if path1 == path2:
            return True
        # Dependência se um é subdiretório do outro
        if path1.startswith(path2) or path2.startswith(path1):
            return True
        return False

    @staticmethod
    def _normalize_path(path: str) -> str:
        # Remove crases e espaços
        return path.replace('`', '').strip().lower()
