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
    _ERR_INVALID_PATH = "Path GitLab inválido: '{repo_name}'. Esperado pelo menos 'namespace/projeto'. Exemplo: 'meugrupo/meuprojeto' ou use o Project ID numérico (recomendado)."
    _ERR_INVALID_FORMAT = "Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"

    def normalize(self, repo_name: str) -> str:
        repo_name = repo_name.strip()
        self._validate_gitlab_format(repo_name)
        try:
            project_id = int(repo_name)
            print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
            return str(project_id)
        except ValueError:
            pass
        if '/' in repo_name:
            parts = [p for p in repo_name.split('/') if p]
            if len(parts) >= 2:
                normalized_path = '/'.join(parts)
                print(f"GitLab path completo detectado: {normalized_path}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
                return normalized_path
        raise HTTPException(
            status_code=400,
            detail=self._ERR_INVALID_FORMAT.format(repo_name=repo_name)
        )

    def _validate_gitlab_format(self, repo_name: str) -> None:
        # Simplificado para fácil manutenção
        validators = [
            lambda v: v.isdigit(),
            lambda v: '/' in v and len([p for p in v.split('/') if p]) >= 2
        ]
        for validate in validators:
            if validate(repo_name):
                return
        # Decide qual mensagem de erro usar
        if '/' in repo_name:
            parts = [p for p in repo_name.split('/') if p]
            if len(parts) < 2:
                raise HTTPException(
                    status_code=400,
                    detail=self._ERR_INVALID_PATH.format(repo_name=repo_name)
                )
        raise HTTPException(
            status_code=400,
            detail=self._ERR_INVALID_FORMAT.format(repo_name=repo_name)
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
        if repository_type == 'gitlab':
            print(f"GitLab - Repo original: '{repo_name}', normalizado: {normalized}")
        return normalized
