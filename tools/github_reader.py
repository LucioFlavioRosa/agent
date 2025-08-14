# Arquivo: tools/github_reader.py (VERSÃO FINAL, ROBUSTA E OTIMIZADA)

import time
import yaml
import os
from github import GithubException, GitTreeElement, UnknownObjectException
from tools.github_connector import GitHubConnector 
from domain.interfaces.repository_reader_interface import IRepositoryReader
import base64

class GitHubRepositoryReader(IRepositoryReader):
    """
    Implementação otimizada e robusta que usa a API Git Trees para leitura rápida de repositórios.
    """
    def __init__(self):
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()

    def _carregar_config_workflows(self):
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
            
            print("Mapeamento de extensões carregado com sucesso.")
            return mapeamento_expandido
        
        # <-- MUDANÇA: Tratamento de erro mais específico -->
        except FileNotFoundError:
            print(f"ERRO CRÍTICO: Arquivo de configuração de workflows não encontrado em '{yaml_path}'.")
            raise
        except yaml.YAMLError as e:
            print(f"ERRO CRÍTICO: Falha ao processar o arquivo YAML '{yaml_path}'. Erro: {e}")
            raise
        except Exception as e:
            print(f"ERRO INESPERADO ao carregar workflows: {e}")
            raise

    def read_repository(self, nome_repo: str, tipo_analise: str, nome_branch: str = None) -> dict:
        print(f"Iniciando leitura otimizada do repositório: {nome_repo}")
        repositorio = GitHubConnector.connection(repositorio=nome_repo)

        if nome_branch is None:
            branch_a_ler = repositorio.default_branch
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}'...")
            
            # <-- MUDANÇA: Tratamento de erro para branch inexistente -->
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                print(f"ERRO CRÍTICO: A branch '{branch_a_ler}' não foi encontrada no repositório '{nome_repo}'.")
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")

            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            print(f"Árvore obtida. {len(tree_elements)} itens totais encontrados.")

            # <-- MUDANÇA: Checagem para repositórios gigantes -->
            if tree_response.truncated:
                print(f"AVISO: A lista de arquivos do repositório '{nome_repo}' foi truncada pela API do GitHub "
                      f"porque contém mais de 100.000 arquivos. A análise será parcial.")

            arquivos_para_ler = [
                element for element in tree_elements
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            # Lê o conteúdo apenas dos arquivos filtrados
            for i, element in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0: # Log de progresso a cada 50 arquivos
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({element.path})")
                try:
                    blob_content = repositorio.get_git_blob(element.sha).content
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                except Exception as e:
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{element.path}'. Pulando. Erro: {e}")

        except GithubException as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API do GitHub: {e}")
            raise
        
        print(f"\nLeitura otimizada concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo
