from typing import Optional, Dict, Any

class AzureReader:
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider

    def read_repository(self, nome_repo: str, tipo_analise: str, branch_name: Optional[str] = None, arquivos_especificos: Optional[list] = None) -> Dict[str, Any]:
        repo = self.repository_provider.get_repository(nome_repo)
        branch = branch_name if branch_name else 'main'
        file_tree = repo.get_file_tree(branch=branch)
        if arquivos_especificos:
            file_tree = [f for f in file_tree if f['path'] in arquivos_especificos]
        conteudo = {}
        for file_info in file_tree:
            path = file_info['path']
            conteudo[path] = repo.get_file_content(path, branch=branch)
        return conteudo
