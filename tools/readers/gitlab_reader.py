import base64
from typing import Dict, Optional, List, Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.readers.base_reader import BaseReader

class GitLabReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or GitLabRepositoryProvider())

    def read_single_file(self, repo_name, file_path: str, branch_name: str) -> Optional[str]:
        print(f"[GitLabReader] Lendo arquivo específico: '{file_path}' na branch '{branch_name}' do repositório '{getattr(repo_name, 'path_with_namespace', 'desconhecido')}'")
        try:
            file_content = repo_name.files.get(file_path=file_path, ref=branch_name)
            decoded = base64.b64decode(file_content.content).decode('utf-8')
            print(f"[GitLabReader] Decodificação bem-sucedida para '{file_path}'")
            return decoded
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg or "not found" in msg:
                print(f"[GitLabReader] AVISO: Arquivo '{file_path}' não encontrado na branch '{branch_name}'.")
                return None
            elif "403" in msg or "forbidden" in msg:
                print(f"[GitLabReader] AVISO: Sem permissão para acessar o arquivo '{file_path}' na branch '{branch_name}'.")
                raise PermissionError(f"Sem permissão para acessar o arquivo '{file_path}' na branch '{branch_name}'.") from e
            else:
                print(f"[GitLabReader] ERRO inesperado ao ler arquivo '{file_path}' na branch '{branch_name}': {e}")
                raise RuntimeError(f"Erro inesperado ao ler arquivo '{file_path}' na branch '{branch_name}': {e}") from e

    def _ler_arquivos_especificos(self, repo_name, branch_name: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        arquivos_lidos = {}
        for i, file_path in enumerate(arquivos_especificos):
            self._log_file_read_progress(i, len(arquivos_especificos), file_path)
            try:
                content = self.read_single_file(repo_name, file_path, branch_name)
                if content is not None:
                    arquivos_lidos[file_path] = content
                else:
                    print(f"[GitLabReader] AVISO: Arquivo '{file_path}' não encontrado ou vazio na branch '{branch_name}'.")
            except PermissionError as e:
                print(f"[GitLabReader] AVISO: Sem permissão para ler o arquivo '{file_path}': {e}")
            except Exception as e:
                print(f"[GitLabReader] AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{file_path}'. Pulando. Erro: {e}")
        return arquivos_lidos

    def _build_gitlab_error_message(self, error_code: str, context: dict) -> str:
        error_messages = {
            'branch_not_found': f"Branch '{context.get('branch')}' não encontrada no repositório GitLab '{context.get('repo')}'. Verifique se a branch existe.",
            'repo_not_found': f"Repositório GitLab '{context.get('repo')}' não encontrado ou sem permissão de acesso.",
            'permission_denied': f"Sem permissão para acessar a árvore do repositório GitLab '{context.get('repo')}'. Verifique as permissões do token.",
            'unexpected': f"Erro inesperado ao obter árvore do repositório GitLab '{context.get('repo')}': {context.get('error')}"
        }
        return error_messages.get(error_code, f"Erro desconhecido: {context.get('error')}")

    def _obter_lista_todos_arquivos(self, repo_name, branch_name: str) -> List[str]:
        repo_namespace = getattr(repo_name, 'path_with_namespace', 'desconhecido')
        print(f"Obtendo lista completa de arquivos GitLab da branch '{branch_name}' do repositório '{repo_namespace}'...")
        try:
            tree_items = repo_name.repository_tree(ref=branch_name, recursive=True, all=True)
        except Exception as e:
            msg = str(e).lower()
            context = {'branch': branch_name, 'repo': repo_namespace, 'error': e}
            error_map = {
                'branch_not_found': lambda m: "branch" in m or "ref" in m,
                'repo_not_found': lambda m: "404" in m or "not found" in m,
                'permission_denied': lambda m: "403" in m or "forbidden" in m,
            }
            for code, check in error_map.items():
                if check(msg):
                    raise ValueError(self._build_gitlab_error_message(code, context)) from e
            raise RuntimeError(self._build_gitlab_error_message('unexpected', context)) from e
        lista_arquivos = [
            item['path'] for item in tree_items
            if item['type'] == 'blob'
        ]
        print(f"Lista completa GitLab obtida: {len(lista_arquivos)} arquivos encontrados.")
        return lista_arquivos

    def _ler_repositorio_completo(self, repo_name, branch_name: str, analysis_type: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        try:
            print(f"Obtendo árvore de arquivos GitLab da branch '{branch_name}' do repositório '{getattr(repo_name, 'path_with_namespace', 'desconhecido')}'...")
            tree_items = repo_name.repository_tree(ref=branch_name, recursive=True, all=True)
            print(f"Árvore GitLab obtida. {len(tree_items)} itens totais encontrados.")
            arquivos_para_ler = [
                item for item in tree_items
                if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in extensoes_alvo)
            ]
            print(f"Filtragem GitLab concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            for i, item in enumerate(arquivos_para_ler):
                self._log_file_read_progress(i, len(arquivos_para_ler), item['path'])
                try:
                    file_content = repo_name.files.get(file_path=item['path'], ref=branch_name)
                    decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                    arquivos_do_repo[item['path']] = decoded_content
                except Exception as e:
                    msg = str(e).lower()
                    if "404" in msg or "not found" in msg:
                        print(f"AVISO: Arquivo '{item['path']}' não encontrado (pode ter sido removido). Pulando.")
                    elif "403" in msg or "forbidden" in msg:
                        print(f"AVISO: Sem permissão para ler o arquivo '{item['path']}'. Pulando.")
                    else:
                        print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{item['path']}'. Pulando. Erro: {e}")
        except Exception as e:
            msg = str(e).lower()
            context = {'branch': branch_name, 'repo': getattr(repo_name, 'path_with_namespace', 'desconhecido'), 'error': e}
            error_map = {
                'branch_not_found': lambda m: "branch" in m or "ref" in m,
                'repo_not_found': lambda m: "404" in m or "not found" in m,
                'permission_denied': lambda m: "403" in m or "forbidden" in m,
            }
            for code, check in error_map.items():
                if check(msg):
                    raise ValueError(self._build_gitlab_error_message(code, context)) from e
            raise RuntimeError(self._build_gitlab_error_message('unexpected', context)) from e
        return arquivos_do_repo

    def read_repository_internal(
        self,
        repository_type: str,
        repo_name,
        branch_name: str = None,
        analysis_type: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = branch_name or 'main'
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada GitLab ativado para {len(arquivos_especificos)} arquivos específicos no repositório '{getattr(repo_name, 'path_with_namespace', 'desconhecido')}'.")
            arquivos_lidos = self._ler_arquivos_especificos(repo_name, branch_a_ler, arquivos_especificos)
        else:
            print(f"Modo de leitura completa GitLab ativado (filtro por extensão) para o repositório '{getattr(repo_name, 'path_with_namespace', 'desconhecido')}'.")
            extensoes_alvo = self._validar_extensoes_alvo(analysis_type, mapeamento_tipo_extensoes)
            arquivos_lidos = self._ler_repositorio_completo(repo_name, branch_a_ler, analysis_type, extensoes_alvo)
        if retornar_lista_arquivos:
            print("Flag retornar_lista_arquivos ativada - obtendo lista completa de arquivos GitLab.")
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repo_name, branch_a_ler)
            return {
                'codigo': arquivos_lidos,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_lidos
