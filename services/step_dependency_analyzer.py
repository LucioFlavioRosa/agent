from typing import Dict

class StepDependencyAnalyzer:
    @staticmethod
    def are_steps_dependent(step1: Dict, step2: Dict) -> bool:
        path1 = StepDependencyAnalyzer._normalize_path(step1.get('Caminho do Arquivo', ''))
        path2 = StepDependencyAnalyzer._normalize_path(step2.get('Caminho do Arquivo', ''))
        if not path1 or not path2:
            return False
        return path1 == path2

    @staticmethod
    def _normalize_path(path: str) -> str:
        return path.replace('`', '').strip().lower()
