import base64
from typing import Dict, Optional, List, Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider
from tools.readers.base_reader import BaseReader

class GitLabReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or GitLabRepositoryProvider())

    def read_repository(
        self,
        repositorio,
        tipo_analise: str,
        nome_branch: Optional[str] = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "GitLab")
        print(f"Obtendo árvore de arquivos GitLab da branch '{branch_a_ler}' do repositório '{repositorio.path_with_namespace}'...")
        try:
            tree_items = repositorio.repository_tree(ref=branch_a_ler, recursive=True, all=True)
            print(f"Árvore GitLab obtida. {len(tree_items)} itens totais encontrados.")
        except Exception as e:
            raise RuntimeError(f"Erro ao obter árvore do repositório GitLab '{repositorio.path_with_namespace}': {e}")
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Filtrando por {len(arquivos_especificos)} arquivos específicos.")
            arquivos_para_ler = [item for item in tree_items if item['type'] == 'blob' and item['path'] in arquivos_especificos]
        else:
            extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
            arquivos_para_ler = [item for item in tree_items if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in extensoes_alvo)]
        print(f"{len(arquivos_para_ler)} arquivos selecionados para leitura de conteúdo.")
        arquivos_do_repo = {}
        for i, item in enumerate(arquivos_para_ler):
            try:
                file_content = repositorio.files.get(file_path=item['path'], ref=branch_a_ler)
                decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                arquivos_do_repo[item['path']] = decoded_content
                print(f"Conteúdo de '{item['path']}' lido com sucesso.")
            except Exception as e:
                print(f"Falha ao ler ou decodificar o conteúdo do arquivo '{item['path']}': {e}")
        if retornar_lista_arquivos:
            lista_todos_arquivos = [item['path'] for item in tree_items if item['type'] == 'blob']
            return {
                'codigo': arquivos_do_repo,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_do_repo
