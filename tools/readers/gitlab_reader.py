import base64
from typing import Dict, Optional, List, Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.readers.base_reader import BaseReader

class GitLabReader(BaseReader):
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None, cache_service=None):
        super().__init__(repository_provider or GitLabRepositoryProvider(), cache_service=cache_service)

    def _extract_repo_info(self, repositorio):
        namespace = getattr(repositorio, 'namespace', None)
        project = getattr(repositorio, 'name', None)
        if hasattr(repositorio, 'path_with_namespace') and repositorio.path_with_namespace:
            parts = repositorio.path_with_namespace.split('/')
            if len(parts) >= 2:
                namespace = '/'.join(parts[:-1])
                project = parts[-1]
        return namespace or '', project or ''

    def _read_gitlab_file(self, repositorio, caminho_arquivo: str, branch_a_ler: str) -> str:
        namespace, project = self._extract_repo_info(repositorio)
        platform = 'gitlab'
        def ler_callback():
            file_content = repositorio.files.get(file_path=caminho_arquivo, ref=branch_a_ler)
            return base64.b64decode(file_content.content).decode('utf-8')
        if self.cache_service:
            return self._ler_conteudo_arquivo_com_cache(
                platform, namespace, '', project, branch_a_ler, caminho_arquivo, ler_callback
            )
        else:
            return ler_callback()

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        return self._ler_arquivos_especificos_base(
            repositorio, branch_a_ler, arquivos_especificos, "GitLab", self._read_gitlab_file
        )

    def _obter_lista_todos_arquivos(self, repositorio, branch_a_ler: str) -> List[str]:
        namespace, project = self._extract_repo_info(repositorio)
        platform = 'gitlab'
        def obter_lista_callback():
            print(f"Obtendo lista completa de arquivos GitLab da branch '{branch_a_ler}' do repositório '{getattr(repositorio, 'path_with_namespace', '')}'...")
            try:
                tree_items = repositorio.repository_tree(ref=branch_a_ler, recursive=True, all=True)
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    if "branch" in str(e).lower() or "ref" in str(e).lower():
                        raise ValueError(
                            f"Branch '{branch_a_ler}' não encontrada no repositório GitLab "
                            f"'{getattr(repositorio, 'path_with_namespace', '')}'. Verifique se a branch existe."
                        ) from e
                    else:
                        raise ValueError(
                            f"Repositório GitLab '{getattr(repositorio, 'path_with_namespace', '')}' não encontrado "
                            f"ou sem permissão de acesso."
                        ) from e
                elif "403" in str(e) or "forbidden" in str(e).lower():
                    raise PermissionError(
                        f"Sem permissão para acessar a árvore do repositório GitLab "
                        f"'{getattr(repositorio, 'path_with_namespace', '')}'. Verifique as permissões do token."
                    ) from e
                else:
                    raise RuntimeError(
                        f"Erro inesperado ao obter árvore do repositório GitLab "
                        f"'{getattr(repositorio, 'path_with_namespace', '')}': {e}"
                    ) from e
            lista_arquivos = [
                item['path'] for item in tree_items
                if item['type'] == 'blob'
            ]
            print(f"Lista completa GitLab obtida: {len(lista_arquivos)} arquivos encontrados.")
            return lista_arquivos
        if self.cache_service:
            return self._obter_lista_todos_arquivos_com_cache(platform, namespace, '', project, branch_a_ler, obter_lista_callback)
        else:
            return obter_lista_callback()

    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        namespace, project = self._extract_repo_info(repositorio)
        platform = 'gitlab'
        try:
            print(f"Obtendo árvore de arquivos GitLab da branch '{branch_a_ler}' do repositório '{getattr(repositorio, 'path_with_namespace', '')}'...")
            try:
                tree_items = repositorio.repository_tree(ref=branch_a_ler, recursive=True, all=True)
                print(f"Árvore GitLab obtida. {len(tree_items)} itens totais encontrados.")
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    if "branch" in str(e).lower() or "ref" in str(e).lower():
                        raise ValueError(
                            f"Branch '{branch_a_ler}' não encontrada no repositório GitLab "
                            f"'{getattr(repositorio, 'path_with_namespace', '')}'. Verifique se a branch existe."
                        ) from e
                    else:
                        raise ValueError(
                            f"Repositório GitLab '{getattr(repositorio, 'path_with_namespace', '')}' não encontrado "
                            f"ou sem permissão de acesso."
                        ) from e
                elif "403" in str(e) or "forbidden" in str(e).lower():
                    raise PermissionError(
                        f"Sem permissão para acessar a árvore do repositório GitLab "
                        f"'{getattr(repositorio, 'path_with_namespace', '')}'. Verifique as permissões do token."
                    ) from e
                else:
                    raise RuntimeError(
                        f"Erro inesperado ao obter árvore do repositório GitLab "
                        f"'{getattr(repositorio, 'path_with_namespace', '')}': {e}"
                    ) from e
            arquivos_para_ler = [
                item for item in tree_items
                if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in extensoes_alvo)
            ]
            print(f"Filtragem GitLab concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            for i, item in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({item['path']})")
                def ler_callback():
                    file_content = repositorio.files.get(file_path=item['path'], ref=branch_a_ler)
                    return base64.b64decode(file_content.content).decode('utf-8')
                if self.cache_service:
                    conteudo = self._ler_conteudo_arquivo_com_cache(platform, namespace, '', project, branch_a_ler, item['path'], ler_callback)
                else:
                    conteudo = ler_callback()
                if conteudo is not None:
                    arquivos_do_repo[item['path']] = conteudo
        except (ValueError, PermissionError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"ERRO CRÍTICO durante a comunicação com a API GitLab "
                f"para o repositório '{getattr(repositorio, 'path_with_namespace', 'desconhecido')}': {e}"
            ) from e
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
        try:
            branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "GitLab")
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"Modo de leitura filtrada GitLab ativado para {len(arquivos_especificos)} arquivos específicos no repositório '{getattr(repositorio, 'path_with_namespace', '')}'.")
                arquivos_lidos = self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
            else:
                print(f"Modo de leitura completa GitLab ativado (filtro por extensão) para o repositório '{getattr(repositorio, 'path_with_namespace', '')}'.")
                extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
                arquivos_lidos = self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)
            if retornar_lista_arquivos:
                print("Flag retornar_lista_arquivos ativada - obtendo lista completa de arquivos GitLab.")
                lista_todos_arquivos = self._obter_lista_todos_arquivos(repositorio, branch_a_ler)
                return {
                    'codigo': arquivos_lidos,
                    'lista_arquivos': lista_todos_arquivos
                }
            else:
                return arquivos_lidos
        except (ValueError, PermissionError, RuntimeError, FileNotFoundError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"Erro inesperado durante a leitura do repositório GitLab "
                f"'{getattr(repositorio, 'path_with_namespace', 'desconhecido')}': {e}"
            ) from e