import base64
from typing import Dict, Optional, List, Union
from github import GithubException, UnknownObjectException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.readers.base_reader import BaseReader

class GitHubReader(BaseReader):
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None, cache_service=None):
        super().__init__(repository_provider or GitHubRepositoryProvider(), cache_service=cache_service)

    def _extract_repo_info(self, repositorio):
        owner = getattr(repositorio, 'owner', None)
        repo_name = getattr(repositorio, 'name', None)
        if hasattr(repositorio, 'full_name') and repositorio.full_name:
            parts = repositorio.full_name.split('/')
            if len(parts) == 2:
                owner, repo_name = parts
        return owner or '', '', repo_name or ''

    def _read_github_file(self, repositorio, caminho_arquivo: str, branch_a_ler: str) -> str:
        owner, _, repo_name = self._extract_repo_info(repositorio)
        platform = 'github'
        def ler_callback():
            file_content = repositorio.get_contents(caminho_arquivo, ref=branch_a_ler)
            return base64.b64decode(file_content.content).decode('utf-8')
        if self.cache_service:
            return self._ler_conteudo_arquivo_com_cache(
                platform, owner, '', repo_name, branch_a_ler, caminho_arquivo, ler_callback
            )
        else:
            return ler_callback()

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        return self._ler_arquivos_especificos_base(
            repositorio, branch_a_ler, arquivos_especificos, "GitHub", self._read_github_file
        )

    def _obter_lista_todos_arquivos(self, repositorio, branch_a_ler: str) -> List[str]:
        owner, _, repo_name = self._extract_repo_info(repositorio)
        platform = 'github'
        def obter_lista_callback():
            print(f"Obtendo lista completa de arquivos GitHub da branch '{branch_a_ler}'...")
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")
            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            lista_arquivos = [
                element.path for element in tree_elements
                if element.type == 'blob'
            ]
            print(f"Lista completa GitHub obtida: {len(lista_arquivos)} arquivos encontrados.")
            return lista_arquivos
        if self.cache_service:
            return self._obter_lista_todos_arquivos_com_cache(platform, owner, '', repo_name, branch_a_ler, obter_lista_callback)
        else:
            return obter_lista_callback()

    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        owner, _, repo_name = self._extract_repo_info(repositorio)
        platform = 'github'
        try:
            print(f"Obtendo a árvore de arquivos GitHub completa da branch '{branch_a_ler}'...")
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")
            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            print(f"Árvore GitHub obtida. {len(tree_elements)} itens totais encontrados.")
            if tree_response.truncated:
                print(f"AVISO: A lista de arquivos do repositório foi truncada pela API.")
            arquivos_para_ler = [
                element for element in tree_elements
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)
            ]
            print(f"Filtragem GitHub concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            for i, element in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({element.path})")
                def ler_callback():
                    blob_content = repositorio.get_git_blob(element.sha).content
                    return base64.b64decode(blob_content).decode('utf-8')
                if self.cache_service:
                    conteudo = self._ler_conteudo_arquivo_com_cache(platform, owner, '', repo_name, branch_a_ler, element.path, ler_callback)
                else:
                    conteudo = ler_callback()
                if conteudo is not None:
                    arquivos_do_repo[element.path] = conteudo
        except GithubException as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API GitHub: {e}")
            raise
        print(f"\nLeitura completa GitHub concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo

    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "GitHub")
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada GitHub ativado para {len(arquivos_especificos)} arquivos específicos.")
            arquivos_lidos = self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa GitHub ativado (filtro por extensão).")
            extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
            arquivos_lidos = self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)
        if retornar_lista_arquivos:
            print("Flag retornar_lista_arquivos ativada - obtendo lista completa de arquivos GitHub.")
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repositorio, branch_a_ler)
            return {
                'codigo': arquivos_lidos,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_lidos
