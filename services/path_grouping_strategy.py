from typing import List, Dict
from tools.repo_committers.path_normalizer import PathNormalizer

class PathGroupingStrategy:
    @staticmethod
    def group_steps_by_path(steps: List[Dict]) -> Dict[str, List[Dict]]:
        grouped = {}
        for step in steps:
            path = step.get('Caminho do Arquivo', '')
            normalized_path = PathNormalizer.normalize_for_grouping(path)
            if not normalized_path:
                continue
            if normalized_path not in grouped:
                grouped[normalized_path] = []
            grouped[normalized_path].append(step)
        # Garantir que todos os passos com o mesmo caminho estejam juntos e ordenados por Passo #
        for group in grouped.values():
            try:
                group.sort(key=lambda x: int(x.get('Passo #', '0')))
            except Exception:
                pass
        return grouped
