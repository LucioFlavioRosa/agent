import base64
from typing import Dict, Optional, List, Union
from github import GithubException, UnknownObjectException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.readers.base_reader import BaseReader

class GitHubReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or GitHubRepositoryProvider())

    def read_repository(
        self,
        repositorio,
        tipo_analise: str,
        nome_branch: Optional[str] = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "GitHub")
        print(f"Obtendo a árvore de arquivos GitHub completa da branch '{branch_a_ler}'...")
        try:
            ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
            tree_sha = ref.object.sha
        except UnknownObjectException:
            raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")
        tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
        tree_elements = tree_response.tree
        print(f"Árvore GitHub obtida. {len(tree_elements)} itens totais encontrados.")
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Filtrando por {len(arquivos_especificos)} arquivos específicos.")
            arquivos_para_ler = [element for element in tree_elements if element.type == 'blob' and element.path in arquivos_especificos]
        else:
            extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
            arquivos_para_ler = [element for element in tree_elements if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)]
        print(f"{len(arquivos_para_ler)} arquivos selecionados para leitura de conteúdo.")
        arquivos_do_repo = {}
        for i, element in enumerate(arquivos_para_ler):
            try:
                blob_content = repositorio.get_git_blob(element.sha).content
                decoded_content = base64.b64decode(blob_content).decode('utf-8')
                arquivos_do_repo[element.path] = decoded_content
                print(f"Conteúdo de '{element.path}' lido com sucesso.")
            except Exception as e:
                print(f"Falha ao ler ou decodificar o conteúdo do arquivo '{element.path}': {e}")
        if retornar_lista_arquivos:
            lista_todos_arquivos = [element.path for element in tree_elements if element.type == 'blob']
            return {
                'codigo': arquivos_do_repo,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_do_repo
