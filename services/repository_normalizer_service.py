from abc import ABC, abstractmethod
from typing import Dict
from fastapi import HTTPException

class RepositoryNormalizerStrategy(ABC):
    """Interface para estratégias de normalização de repositório."""
    
    @abstractmethod
    def normalize(self, repo_name: str) -> str:
        """Normaliza o nome do repositório de acordo com o tipo específico."""
        pass

class GitLabNormalizerStrategy(RepositoryNormalizerStrategy):
    """Estratégia de normalização para repositórios GitLab."""
    
    def normalize(self, repo_name: str) -> str:
        """Normaliza nome de repositório GitLab."""
        repo_name = repo_name.strip()
        
        # Tenta interpretar como Project ID numérico
        try:
            project_id = int(repo_name)
            print(f"GitLab Project ID detectado: {project_id}. Usando formato numérico para máxima robustez.")
            return str(project_id)
        except ValueError:
            pass
        
        # Trata como path completo
        if '/' in repo_name:
            parts = [p for p in repo_name.split('/') if p]
            
            if len(parts) >= 2:
                normalized_path = '/'.join(parts)
                print(f"GitLab path completo detectado: {normalized_path}. RECOMENDAÇÃO: Use o Project ID numérico para máxima robustez contra renomeações.")
                return normalized_path
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Path GitLab inválido: '{repo_name}'. Esperado pelo menos 'namespace/projeto'. Exemplo: 'meugrupo/meuprojeto' ou use o Project ID numérico (recomendado)."
                )
        
        raise HTTPException(
            status_code=400,
            detail=f"Formato de repositório GitLab inválido: '{repo_name}'. Use o Project ID numérico (RECOMENDADO para máxima robustez) ou o path completo 'namespace/projeto'. Exemplos: Project ID: '123456', Path: 'meugrupo/meuprojeto'"
        )

class DefaultNormalizerStrategy(RepositoryNormalizerStrategy):
    """Estratégia padrão que retorna o nome sem modificação."""
    
    def normalize(self, repo_name: str) -> str:
        """Retorna o nome do repositório sem modificação."""
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
        """Registra uma nova estratégia de normalização."""
        self._strategies[repository_type] = strategy
    
    def normalize_repo_name(self, repo_name: str, repository_type: str) -> str:
        """Normaliza o nome do repositório de acordo com seu tipo."""
        strategy = self._strategies.get(repository_type)
        
        if not strategy:
            # Usa estratégia padrão para tipos não registrados
            strategy = DefaultNormalizerStrategy()
        
        normalized = strategy.normalize(repo_name)
        
        if repository_type == 'gitlab':
            print(f"GitLab - Repo original: '{repo_name}', normalizado: {normalized}")
        
        return normalized
