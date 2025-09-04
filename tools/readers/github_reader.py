import base64
from typing import Dict, Optional, List
from github import GithubException, UnknownObjectException
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider

class GitHubReader:
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        self.repository_provider = repository_provider or GitHubRepositoryProvider()

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada GitHub ativado. Lendo {total_arquivos} arquivos específicos...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                file_content = repositorio.get_contents(caminho_arquivo, ref=branch_a_ler)
                decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                arquivos_lidos[caminho_arquivo] = decoded_content
                
            except UnknownObjectException:
                print(f"  [AVISO] Arquivo '{caminho_arquivo}' não encontrado na branch '{branch_a_ler}'. Ignorando.")
            except Exception as e:
                print(f"  [AVISO] Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"Leitura filtrada GitHub concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos

    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
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
                
                try:
                    blob_content = repositorio.get_git_blob(element.sha).content
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
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        if nome_branch is None:
            branch_a_ler = repositorio.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão GitHub: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada GitHub ativado para {len(arquivos_especificos)} arquivos específicos.")
            return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa GitHub ativado (filtro por extensão).")
            extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
            if extensoes_alvo is None:
                raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")
            return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)