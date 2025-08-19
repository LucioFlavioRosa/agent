import time
import yaml
import os
from github import GithubException, GitTreeElement, UnknownObjectException, Repository
from typing import Dict, Optional
from domain.interfaces.repository_reader_interface import IRepositoryReader
import base64

class GitHubRepositoryReader(IRepositoryReader):
    """
    Implementação que lê os arquivos de um objeto de repositório já autenticado,
    usando a API Git Trees para performance.
    """
    def __init__(self):
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()

    def _carregar_config_workflows(self):
        # (Esta função auxiliar não precisa de nenhuma mudança)
        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '..'))
            yaml_path = os.path.join(project_root, 'workflows.yaml')
            
            print(f"Carregando mapeamento de extensões do arquivo: {yaml_path}")
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            mapeamento_expandido = {}
            for workflow_name, data in config.items():
                extensions = data.get('extensions', [])
                if not extensions:
                    continue
                
                mapeamento_expandido[workflow_name.lower()] = extensions
                for step in data.get('steps', []):
                    params = step.get('params', {})
                    tipo_analise_step = params.get('tipo_analise')
                    if tipo_analise_step:
                        mapeamento_expandido[tipo_analise_step.lower()] = extensions
            
            return mapeamento_expandido
        except Exception as e:
            print(f"ERRO INESPERADO ao carregar workflows: {e}")
            raise

    def read_repository(self, repositorio: Repository.Repository, tipo_analise: str, nome_branch: Optional[str] = None) -> Dict[str, str]:
        """
        Lê os arquivos de um objeto de repositório já autenticado.

        Args:
            repositorio (Repository): A instância do repositório já conectada (via PyGithub).
            tipo_analise (str): O tipo de análise para filtrar as extensões de arquivo.
            nome_branch (Optional[str]): O nome da branch a ser lida. Se None, usa a padrão.
        """
        print(f"Iniciando leitura otimizada do repositório: {repositorio.full_name}")

        if nome_branch is None:
            branch_a_ler = repositorio.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado em workflows.yaml")

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}'...")
            
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada no repositório.")

            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree

            if tree_response.truncated:
                print(f"AVISO: A lista de arquivos do repositório foi truncada pela API.")

            arquivos_para_ler = [
                element for element in tree_elements
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            for element in arquivos_para_ler:
                try:
                    blob_content = repositorio.get_git_blob(element.sha).content
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                except Exception as e:
                    print(f"AVISO: Falha ao ler o conteúdo do arquivo '{element.path}'. Pulando. Erro: {e}")

        except GithubException as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API do GitHub: {e}")
            raise
        
        print(f"\nLeitura otimizada concluída. Total de {len(arquivos_do_repo)} arquivos lidos.")
        return arquivos_do_repo
