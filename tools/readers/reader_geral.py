from typing import Optional, Dict, Any
from tools.readers.azure_reader import AzureReader
from tools.readers.github_reader import GithubReader
from tools.readers.gitlab_reader import GitlabReader

class ReaderGeral:
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider
        self.azure_reader = AzureReader(repository_provider=repository_provider)
        self.github_reader = GithubReader(repository_provider=repository_provider)
        self.gitlab_reader = GitlabReader(repository_provider=repository_provider)

    def read_repository(self, nome_repo: str, tipo_analise: str, repository_type: str, branch_name: Optional[str] = None, arquivos_especificos: Optional[list] = None) -> Dict[str, Any]:
        if repository_type == 'azure':
            return self.azure_reader.read_repository(nome_repo, tipo_analise, branch_name=branch_name, arquivos_especificos=arquivos_especificos)
        elif repository_type == 'github':
            return self.github_reader.read_repository(nome_repo, tipo_analise, branch_name=branch_name, arquivos_especificos=arquivos_especificos)
        elif repository_type == 'gitlab':
            return self.gitlab_reader.read_repository(nome_repo, tipo_analise, branch_name=branch_name, arquivos_especificos=arquivos_especificos)
        else:
            raise ValueError(f"Tipo de repositório '{repository_type}' não suportado.")
