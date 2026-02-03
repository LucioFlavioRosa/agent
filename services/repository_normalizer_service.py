from abc import ABC, abstractmethod
from typing import Dict
from fastapi import HTTPException

class RepositoryNormalizerStrategy(ABC):
    """Interface para estratégias de normalização de repositório."""
    @abstractmethod
    def normalize(self, repo_name: str) -> str:
        pass

class GitLabNormalizerStrategy(RepositoryNormalizerStrategy):
    """Estratégia de normalização para repositórios GitLab."""
    def normalize(self, repo_name: str) -> str:
        repo_name = repo_name.strip()
        # Se for Project ID numérico
        try:
            project_id = int(repo_name)
            return str(project_id)
        except ValueError:
            pass
        # Se for path completo 'namespace/projeto'
        if '/' in repo_name:
            parts = [p for p in repo_name.split('/') if p]
            if len(parts) >= 2:
                return '/'.join(parts)
        raise HTTPException(
            status_code=400,
            detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico ou o path completo 'namespace/projeto'."
        )

class DefaultNormalizerStrategy(RepositoryNormalizerStrategy):
    """Estratégia padrão que retorna o nome sem modificação."""
    def normalize(self, repo_name: str) -> str:
        return repo_name

class RepositoryNormalizerService:
    """Serviço para normalização de nomes de repositório usando padrão Strategy."""
    def __init__(self):
        self._strategies: Dict[str, RepositoryNormalizerStrategy] = {
            'gitlab': GitLabNormalizerStrategy(),
            'github': DefaultNormalizerStrategy(),
            'azure': DefaultNormalizerStrategy()
        }
    def register_strategy(self, repository_type: str, strategy: RepositoryNormalizerStrategy) -> None:
        self._strategies[repository_type] = strategy
    def normalize_repo_name(self, repo_name: str, repository_type: str) -> str:
        strategy = self._strategies.get(repository_type)
        if not strategy:
            strategy = DefaultNormalizerStrategy()
        normalized = strategy.normalize(repo_name)
        return normalized
