# Arquivo: tools/github_reader.py (VERSÃO OTIMIZADA COM GIT TREES API)

import time
import yaml
import os
from github import GithubException, GitTreeElement
from tools.github_connector import GitHubConnector 
from domain.interfaces.repository_reader_interface import IRepositoryReader
import base64

class GitHubRepositoryReader(IRepositoryReader):
    """
    Implementação otimizada que usa a API Git Trees para leitura rápida de repositórios.
    """
    def __init__(self):
        self._mapeamento_tipo_extensoes = self._carregar_config_workflows()

    def _carregar_config_workflows(self):
        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, '..'))
            yaml_path = os.path.join(project_root, 'workflows.yaml')
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
            print(f"ERRO ao ler ou processar 'workflows.yaml': {e}")
            return {}

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
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado em workflows.yaml")

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}' em uma única chamada de API...")
            # Obtém a referência da branch para pegar o SHA do último commit
            ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
            # Obtém a árvore de arquivos completa recursivamente
            tree = repositorio.get_git_tree(ref.object.sha, recursive=True).tree
            print(f"Árvore obtida. {len(tree)} itens encontrados. Filtrando e lendo arquivos relevantes...")

            arquivos_para_ler = []
            for element in tree:
                # Filtra apenas por arquivos ('blob') que correspondem às extensões
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo):
                    arquivos_para_ler.append(element)
            
            print(f"Encontrados {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo}. Lendo o conteúdo...")
            
            # Agora, lê o conteúdo apenas dos arquivos filtrados
            for element in arquivos_para_ler:
                try:
                    # O conteúdo do blob é em base64, então precisa ser decodificado
                    blob_content = repositorio.get_git_blob(element.sha).content
                    decoded_content = base64.b64decode(blob_content).decode('utf-8')
                    arquivos_do_repo[element.path] = decoded_content
                except Exception as e:
                    print(f"AVISO: Falha ao decodificar o conteúdo do arquivo '{element.path}'. Pulando. Erro: {e}")

        except GithubException as e:
            print(f"ERRO CRÍTICO ao ler o repositório via API Git Trees: {e}")
            raise # Re-lança a exceção para que o orchestrator possa lidar com ela
        
        print(f"\nLeitura otimizada concluída. Total de {len(arquivos_do_repo)} arquivos lidos.")
        return arquivos_do_repo
