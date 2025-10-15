import os
from typing import Dict, Optional, List

class RepositoryFilterService:
    @staticmethod
    def filter_by_specific_files(repository_content: Dict[str, str], arquivos_especificos: Optional[List[str]]) -> Dict[str, str]:
        if not arquivos_especificos:
            return repository_content
        arquivos_especificos_normalizados = set()
        for path in arquivos_especificos:
            p = path.lstrip('/').lower()
            arquivos_especificos_normalizados.add(p)
        resultado = {}
        for repo_path, conteudo in repository_content.items():
            repo_path_normalizado = repo_path.lstrip('/').lower()
            if repo_path_normalizado in arquivos_especificos_normalizados:
                resultado[repo_path] = conteudo
        return resultado
