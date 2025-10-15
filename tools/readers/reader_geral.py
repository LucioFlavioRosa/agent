from typing import Dict, Optional, List, Union
from tools.readers.azure_reader import AzureReader
from tools.readers.github_reader import GitHubReader
from tools.readers.gitlab_reader import GitLabReader

class ReaderGeral:
    def __init__(self, repository_provider=None):
        self.repository_provider = repository_provider
        self.azure_reader = AzureReader()
        self.github_reader = GitHubReader()
        self.gitlab_reader = GitLabReader()

    def read_repository(
        self,
        repositorio,
        tipo_analise: str,
        nome_branch: Optional[str] = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        repo_type = getattr(repositorio, 'tipo', None) or getattr(repositorio, 'repository_type', None)
        if repo_type == 'azure':
            return self.azure_reader.read_repository(
                repositorio,
                tipo_analise,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos,
                mapeamento_tipo_extensoes=mapeamento_tipo_extensoes,
                retornar_lista_arquivos=retornar_lista_arquivos
            )
        elif repo_type == 'github':
            return self.github_reader.read_repository(
                repositorio,
                tipo_analise,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos,
                mapeamento_tipo_extensoes=mapeamento_tipo_extensoes,
                retornar_lista_arquivos=retornar_lista_arquivos
            )
        elif repo_type == 'gitlab':
            return self.gitlab_reader.read_repository(
                repositorio,
                tipo_analise,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos,
                mapeamento_tipo_extensoes=mapeamento_tipo_extensoes,
                retornar_lista_arquivos=retornar_lista_arquivos
            )
        else:
            raise ValueError(f"Tipo de repositório não suportado: {repo_type}")
