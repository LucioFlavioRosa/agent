import base64
from typing import Dict, Optional, List, Union
from github import GithubException, UnknownObjectException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.readers.base_reader import BaseReader
from tools.readers.base_file_reader import BaseFileReader
from tools.user_email_parser import UserEmailParser

class GitHubReader(BaseFileReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None):
        super().__init__(repository_provider or GitHubRepositoryProvider(), user_email=user_email, group_resolver=group_resolver)

    def read_single_file(self, repo_name, file_path: str, branch_name: str) -> Optional[str]:
        repo_desc = getattr(repo_name, 'full_name', 'desconhecido')
        return self._read_file_with_error_handling(
            lambda file_path, ref: repo_name.get_contents(file_path, ref=ref),
            file_path,
            branch_name,
            repo_desc
        )

    def _ler_arquivos_especificos(self, repo_name, branch_name: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        arquivos_lidos = {}
        for file_path in arquivos_especificos:
            try:
                content = self.read_single_file(repo_name, file_path, branch_name)
                if content is not None:
                    arquivos_lidos[file_path] = content
            except PermissionError:
                pass
            except Exception:
                pass
        return arquivos_lidos

    def _obter_lista_todos_arquivos(self, repo_name, branch_name: str) -> List[str]:
        try:
            ref = repo_name.get_git_ref(f"heads/{branch_name}")
            tree_sha = ref.object.sha
            tree_response = repo_name.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            lista_arquivos = [element.path for element in tree_elements if element.type == 'blob']
            return lista_arquivos
        except GithubException:
            raise

    def _ler_repositorio_completo(self, repo_name, branch_name: str, analysis_type: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        try:
            ref = repo_name.get_git_ref(f"heads/{branch_name}")
            tree_sha = ref.object.sha
            tree_response = repo_name.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            arquivos_para_ler = [element for element in tree_elements if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)]
            for element in arquivos_para_ler:
                try:
                    blob_content = repo_name.get_git_blob(element.sha).content
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                except Exception:
                    pass
        except GithubException:
            raise
        return arquivos_do_repo

    def read_repository_internal(
        self,
        repository_type: str,
        repo_name,
        branch_name: str = None,
        analysis_type: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False,
        user_email: Optional[str] = None,
        group_resolver: Optional['MongoDBGroupResolverService'] = None
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = branch_name or 'main'
        if arquivos_especificos and len(arquivos_especificos) > 0:
            arquivos_lidos = self._ler_arquivos_especificos(repo_name, branch_a_ler, arquivos_especificos)
        else:
            extensoes_alvo = self._validar_extensoes_alvo(analysis_type, mapeamento_tipo_extensoes)
            arquivos_lidos = self._ler_repositorio_completo(repo_name, branch_a_ler, analysis_type, extensoes_alvo)
        if retornar_lista_arquivos:
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repo_name, branch_a_ler)
            return {
                'codigo': arquivos_lidos,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_lidos
