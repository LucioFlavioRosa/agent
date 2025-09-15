from abc import ABC, abstractmethod
from typing import Dict, Type
from fastapi import HTTPException

class RepositoryNormalizer(ABC):
    @abstractmethod
    def normalize(self, repo_name: str) -> str:
        pass

class GitlabNormalizer(RepositoryNormalizer):
    def normalize(self, repo_name: str) -> str:
        repo_name = repo_name.strip()
        
        try:
            project_id = int(repo_name)
            print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
            return str(project_id)
        except ValueError:
            pass
        
        if '/' in repo_name:
            parts = repo_name.split('/')
            if len(parts) >= 2:
                print(f"GitLab path completo detectado: {repo_name}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
                return repo_name
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Path GitLab inválido: '{repo_name}'. Esperado pelo menos 'namespace/projeto'. Exemplo: 'meugrupo/meuprojeto' ou use o Project ID numérico (recomendado)."
                )
        
        raise HTTPException(
            status_code=400,
            detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"
        )

class DefaultNormalizer(RepositoryNormalizer):
    def normalize(self, repo_name: str) -> str:
        return repo_name

class RepositoryNormalizerRegistry:
    def __init__(self):
        self._normalizers: Dict[str, RepositoryNormalizer] = {
            'gitlab': GitlabNormalizer(),
            'github': DefaultNormalizer(),
            'azure': DefaultNormalizer()
        }
    
    def register_normalizer(self, repository_type: str, normalizer: RepositoryNormalizer) -> None:
        self._normalizers[repository_type] = normalizer
    
    def normalize_repo_name(self, repo_name: str, repository_type: str) -> str:
        normalizer = self._normalizers.get(repository_type, DefaultNormalizer())
        normalized = normalizer.normalize(repo_name)
        if repository_type == 'gitlab':
            print(f"GitLab - Repo original: '{repo_name}', normalizado: '{normalized}'")
        return normalized