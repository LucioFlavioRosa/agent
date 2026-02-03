import base64
from typing import Dict, Optional, List, Union
from github import GithubException, UnknownObjectException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
from tools.readers.base_reader import BaseReader
from tools.user_email_parser import UserEmailParser

class GitHubReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None, user_email: Optional[str] = None, group_resolver: Optional['MongoDBGroupResolverService'] = None):
        super().__init__(repository_provider or GitHubRepositoryProvider())
        self.user_email = user_email
        self.group_resolver = group_resolver
        if user_email:
            self.usuario, self.empresa, self.grupo = self._extract_user_and_company_from_email(user_email, group_resolver)
        else:
            self.usuario, self.empresa, self.grupo = None, None, None

    def _extract_user_and_company_from_email(self, user_email: str, group_resolver: Optional['MongoDBGroupResolverService'] = None):
        return UserEmailParser.parse_email_with_group(user_email, group_resolver)

    def read_single_file(self, repo_name, file_path: str, branch_name: str) -> Optional[str]:
        print(f"[GitHubReader] Lendo arquivo específico: '{file_path}' na branch '{branch_name}'")
        try:
            file_content = repo_name.get_contents(file_path, ref=branch_name)
            print(f"[GitHubReader] Conteúdo bruto retornado para '{file_path}': {type(file_content.content)}")
            decoded = base64.b64decode(file_content.content).decode('utf-8')
            print(f"[GitHubReader] Decodificação bem-sucedida para '{file_path}'")
            return decoded
        except UnknownObjectException:
            print(f"[GitHubReader] AVISO: Arquivo '{file_path}' não encontrado na branch '{branch_name}'.")
            return None
        except GithubException as e:
            if hasattr(e, 'status') and e.status == 404:
                print(f"[GitHubReader] AVISO: Arquivo '{file_path}' não encontrado (404) na branch '{branch_name}'.")
                return None
            elif hasattr(e, 'status') and e.status == 403:
                print(f"[GitHubReader] AVISO: Sem permissão para acessar o arquivo '{file_path}' na branch '{branch_name}'.")
                raise PermissionError(f"Sem permissão para acessar o arquivo '{file_path}' na branch '{branch_name}'.") from e
            else:
                print(f"[GitHubReader] ERRO inesperado ao ler arquivo '{file_path}' na branch '{branch_name}': {e}")
                raise RuntimeError(f"Erro inesperado ao ler arquivo '{file_path}' na branch '{branch_name}': {e}") from e
        except Exception as e:
            print(f"[GitHubReader] ERRO CRÍTICO ao ler arquivo '{file_path}' na branch '{branch_name}': {e}")
            raise

    def _ler_arquivos_especificos(self, repo_name, branch_name: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        arquivos_lidos = {}
        for i, file_path in enumerate(arquivos_especificos):
            self._log_file_read_progress(i, len(arquivos_especificos), file_path)
            try:
                content = self.read_single_file(repo_name, file_path, branch_name)
                if content is not None:
                    arquivos_lidos[file_path] = content
                else:
                    print(f"[GitHubReader] AVISO: Arquivo '{file_path}' não encontrado ou vazio na branch '{branch_name}'.")
            except PermissionError as e:
                print(f"[GitHubReader] AVISO: Sem permissão para ler o arquivo '{file_path}': {e}")
            except Exception as e:
                print(f"[GitHubReader] AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{file_path}'. Pulando. Erro: {e}")
        return arquivos_lidos

    def _obter_lista_todos_arquivos(self, repo_name, branch_name: str) -> List[str]:
        try:
            print(f"Obtendo lista completa de arquivos GitHub da branch '{branch_name}'...")
            try:
                ref = repo_name.get_git_ref(f"heads/{branch_name}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_name}' não encontrada.")
            tree_response = repo_name.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            lista_arquivos = [
                element.path for element in tree_elements
                if element.type == 'blob'
            ]
            print(f"Lista completa GitHub obtida: {len(lista_arquivos)} arquivos encontrados.")
            return lista_arquivos
        except GithubException as e:
            print(f"ERRO ao obter lista completa de arquivos GitHub: {e}")
            raise

    def _ler_repositorio_completo(self, repo_name, branch_name: str, analysis_type: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos GitHub completa da branch '{branch_name}'...")
            try:
                ref = repo_name.get_git_ref(f"heads/{branch_name}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_name}' não encontrada.")
            tree_response = repo_name.get_git_tree(tree_sha, recursive=True)
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
                self._log_file_read_progress(i, len(arquivos_para_ler), element.path)
                try:
                    blob_content = repo_name.get_git_blob(element.sha).content
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                except Exception as e:
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{element.path}'. Pulando. Erro: {e}")
        except GithubException as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API GitHub: {e}")
            raise
        print(f"\nLeitura completa GitHub concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
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
        if user_email:
            usuario, empresa, grupo = self._extract_user_and_company_from_email(user_email, group_resolver)
        else:
            usuario, empresa, grupo = None, None, None
        # Aqui, se for necessário obter o repo via conector, passaria grupo/empresa
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada GitHub ativado para {len(arquivos_especificos)} arquivos específicos.")
            arquivos_lidos = self._ler_arquivos_especificos(repo_name, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa GitHub ativado (filtro por extensão).")
            extensoes_alvo = self._validar_extensoes_alvo(analysis_type, mapeamento_tipo_extensoes)
            arquivos_lidos = self._ler_repositorio_completo(repo_name, branch_a_ler, analysis_type, extensoes_alvo)
        if retornar_lista_arquivos:
            print("Flag retornar_lista_arquivos ativada - obtendo lista completa de arquivos GitHub.")
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repo_name, branch_a_ler)
            return {
                'codigo': arquivos_lidos,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_lidos
