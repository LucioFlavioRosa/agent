import base64
from typing import Dict, Optional, List
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.readers.base_reader import BaseReader

class GitLabReader(BaseReader):
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or GitLabRepositoryProvider())

    def _read_gitlab_file(self, repositorio, caminho_arquivo: str, branch_a_ler: str) -> str:
        try:
            file_content = repositorio.files.get(file_path=caminho_arquivo, ref=branch_a_ler)
            return base64.b64decode(file_content.content).decode('utf-8')
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise FileNotFoundError(
                    f"Arquivo '{caminho_arquivo}' não encontrado na branch '{branch_a_ler}' "
                    f"do repositório GitLab '{repositorio.path_with_namespace}'."
                ) from e
            elif "403" in str(e) or "forbidden" in str(e).lower():
                raise PermissionError(
                    f"Sem permissão para acessar o arquivo '{caminho_arquivo}' "
                    f"no repositório GitLab '{repositorio.path_with_namespace}'. "
                    f"Verifique as permissões do token."
                ) from e
            else:
                raise RuntimeError(
                    f"Erro inesperado ao ler arquivo '{caminho_arquivo}' "
                    f"do repositório GitLab '{repositorio.path_with_namespace}': {e}"
                ) from e

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        return self._ler_arquivos_especificos_base(
            repositorio, branch_a_ler, arquivos_especificos, "GitLab", self._read_gitlab_file
        )

    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        
        try:
            print(f"Obtendo árvore de arquivos GitLab da branch '{branch_a_ler}' do repositório '{repositorio.path_with_namespace}'...")
            
            try:
                tree_items = repositorio.repository_tree(ref=branch_a_ler, recursive=True, all=True)
                print(f"Árvore GitLab obtida. {len(tree_items)} itens totais encontrados.")
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    if "branch" in str(e).lower() or "ref" in str(e).lower():
                        raise ValueError(
                            f"Branch '{branch_a_ler}' não encontrada no repositório GitLab "
                            f"'{repositorio.path_with_namespace}'. Verifique se a branch existe."
                        ) from e
                    else:
                        raise ValueError(
                            f"Repositório GitLab '{repositorio.path_with_namespace}' não encontrado "
                            f"ou sem permissão de acesso."
                        ) from e
                elif "403" in str(e) or "forbidden" in str(e).lower():
                    raise PermissionError(
                        f"Sem permissão para acessar a árvore do repositório GitLab "
                        f"'{repositorio.path_with_namespace}'. Verifique as permissões do token."
                    ) from e
                else:
                    raise RuntimeError(
                        f"Erro inesperado ao obter árvore do repositório GitLab "
                        f"'{repositorio.path_with_namespace}': {e}"
                    ) from e
            
            arquivos_para_ler = [
                item for item in tree_items
                if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem GitLab concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            for i, item in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({item['path']})")
                
                try:
                    file_content = repositorio.files.get(file_path=item['path'], ref=branch_a_ler)
                    decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                    arquivos_do_repo[item['path']] = decoded_content
                    
                except Exception as e:
                    if "404" in str(e) or "not found" in str(e).lower():
                        print(f"AVISO: Arquivo '{item['path']}' não encontrado (pode ter sido removido). Pulando.")
                    elif "403" in str(e) or "forbidden" in str(e).lower():
                        print(f"AVISO: Sem permissão para ler o arquivo '{item['path']}'. Pulando.")
                    else:
                        print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{item['path']}'. Pulando. Erro: {e}")

        except (ValueError, PermissionError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"ERRO CRÍTICO durante a comunicação com a API GitLab "
                f"para o repositório '{repositorio.path_with_namespace}': {e}"
            ) from e
        
        return arquivos_do_repo

    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        try:
            branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "GitLab")
            
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"Modo de leitura filtrada GitLab ativado para {len(arquivos_especificos)} arquivos específicos no repositório '{repositorio.path_with_namespace}'.")
                return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
            else:
                print(f"Modo de leitura completa GitLab ativado (filtro por extensão) para o repositório '{repositorio.path_with_namespace}'.")
                extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
                return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)
                
        except (ValueError, PermissionError, RuntimeError, FileNotFoundError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"Erro inesperado durante a leitura do repositório GitLab "
                f"'{getattr(repositorio, 'path_with_namespace', 'desconhecido')}': {e}"
            ) from e