import time
import yaml
import os
from github import GithubException, GitTreeElement, UnknownObjectException
from tools.github_connector import GitHubConnector 
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.github_repository_provider import GitHubRepositoryProvider
import base64
import requests
from typing import Dict, Optional, List, Union

class GitHubRepositoryReader(IRepositoryReader):
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        self.repository_provider = repository_provider or GitHubRepositoryProvider()
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
            print(f"ERRO INESPERADO ao carregar workflows: {e}")
            raise

    def _is_gitlab_project(self, repositorio) -> bool:
        return hasattr(repositorio, 'web_url') or 'gitlab' in str(type(repositorio)).lower()

    def _is_azure_repo(self, repositorio) -> bool:
        return isinstance(repositorio, dict) and repositorio.get('_provider_type') == 'azure_devops'

    def _get_azure_auth_headers(self, repositorio_dict: dict) -> dict:
        from tools.github_connector import GitHubConnector
        connector = GitHubConnector.create_with_defaults()
        organization = repositorio_dict.get('_organization')
        token = connector._get_token_for_org(organization, 'azure')
        
        import base64
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }

    def _ler_arquivos_especificos_azure(self, repositorio_dict: dict, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada Azure DevOps ativado. Lendo {total_arquivos} arquivos específicos...")
        
        organization = repositorio_dict.get('_organization')
        project = repositorio_dict.get('_project')
        repository = repositorio_dict.get('_repository')
        
        headers = self._get_azure_auth_headers(repositorio_dict)
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                url = f"{base_url}/items?path={caminho_arquivo}&includeContent=true&versionDescriptor.version={branch_a_ler}&api-version=7.0"
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get('content', '')
                    arquivos_lidos[caminho_arquivo] = content
                else:
                    print(f"  [AVISO] Arquivo '{caminho_arquivo}' não encontrado ou inacessível (status: {response.status_code}). Ignorando.")
                    
            except Exception as e:
                print(f"  [AVISO] Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"Leitura filtrada Azure DevOps concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos

    def _ler_repositorio_completo_azure(self, repositorio_dict: dict, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        
        organization = repositorio_dict.get('_organization')
        project = repositorio_dict.get('_project')
        repository = repositorio_dict.get('_repository')
        
        headers = self._get_azure_auth_headers(repositorio_dict)
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
        
        try:
            print(f"Obtendo árvore de arquivos Azure DevOps da branch '{branch_a_ler}'...")
            
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_a_ler}&api-version=7.0"
            response = requests.get(items_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Erro ao obter lista de arquivos: {response.status_code} - {response.text}")
            
            items_data = response.json()
            all_items = items_data.get('value', [])
            
            print(f"Árvore Azure DevOps obtida. {len(all_items)} itens totais encontrados.")
            
            arquivos_para_ler = [
                item for item in all_items
                if not item.get('isFolder', True) and any(item.get('path', '').endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem Azure DevOps concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            for i, item in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0:
                    print(f"  ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({item.get('path')})")
                
                try:
                    file_path = item.get('path')
                    content_url = f"{base_url}/items?path={file_path}&includeContent=true&versionDescriptor.version={branch_a_ler}&api-version=7.0"
                    content_response = requests.get(content_url, headers=headers, timeout=30)
                    
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        file_content = content_data.get('content', '')
                        arquivos_do_repo[file_path] = file_content
                    else:
                        print(f"AVISO: Falha ao ler conteúdo do arquivo '{file_path}' (status: {content_response.status_code}). Pulando.")
                        
                except Exception as e:
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{item.get('path')}'. Pulando. Erro: {e}")

        except Exception as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API Azure DevOps: {e}")
            raise
        
        print(f"\nLeitura completa Azure DevOps concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo

    def _ler_arquivos_especificos_gitlab(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada GitLab ativado. Lendo {total_arquivos} arquivos específicos...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                file_content = repositorio.files.get(file_path=caminho_arquivo, ref=branch_a_ler)
                decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                arquivos_lidos[caminho_arquivo] = decoded_content
                
            except Exception as e:
                print(f"  [AVISO] Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"Leitura filtrada GitLab concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        if self._is_azure_repo(repositorio):
            return self._ler_arquivos_especificos_azure(repositorio, branch_a_ler, arquivos_especificos)
        
        if self._is_gitlab_project(repositorio):
            return self._ler_arquivos_especificos_gitlab(repositorio, branch_a_ler, arquivos_especificos)
        
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada ativado. Lendo {total_arquivos} arquivos específicos...")
        
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
        
        print(f"Leitura filtrada concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos

    def read_repository(
        self, 
        nome_repo: str, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        provider_name = type(self.repository_provider).__name__
        print(f"Iniciando leitura do repositório: {nome_repo} via {provider_name}")

        connector = GitHubConnector(repository_provider=self.repository_provider)
        
        repository_type = 'github'
        if 'GitLab' in provider_name:
            repository_type = 'gitlab'
        elif 'Azure' in provider_name:
            repository_type = 'azure'
        
        repositorio = connector.connection(repositorio=nome_repo, repository_type=repository_type)

        if nome_branch is None:
            if hasattr(repositorio, 'default_branch'):
                branch_a_ler = repositorio.default_branch
            elif isinstance(repositorio, dict) and 'default_branch' in repositorio:
                branch_a_ler = repositorio['default_branch']
            else:
                branch_a_ler = 'main'
            print(f"Nenhuma branch especificada. Usando a branch padrão: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada ativado para {len(arquivos_especificos)} arquivos específicos.")
            return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa ativado (filtro por extensão).")
            return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise)
    
    def _ler_repositorio_completo_gitlab(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        
        try:
            print(f"Obtendo árvore de arquivos GitLab da branch '{branch_a_ler}'...")
            
            tree_items = repositorio.repository_tree(ref=branch_a_ler, recursive=True, all=True)
            print(f"Árvore GitLab obtida. {len(tree_items)} itens totais encontrados.")
            
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
                    print(f"AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{item['path']}'. Pulando. Erro: {e}")

        except Exception as e:
            print(f"ERRO CRÍTICO durante a comunicação com a API GitLab: {e}")
            raise
        
        return arquivos_do_repo
    
    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str) -> Dict[str, str]:
        extensoes_alvo = self._mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")

        if self._is_azure_repo(repositorio):
            return self._ler_repositorio_completo_azure(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)

        if self._is_gitlab_project(repositorio):
            return self._ler_repositorio_completo_gitlab(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)

        arquivos_do_repo = {}
        try:
            print(f"Obtendo a árvore de arquivos completa da branch '{branch_a_ler}'...")
            
            try:
                ref = repositorio.get_git_ref(f"heads/{branch_a_ler}")
                tree_sha = ref.object.sha
            except UnknownObjectException:
                raise ValueError(f"Branch '{branch_a_ler}' não encontrada.")

            tree_response = repositorio.get_git_tree(tree_sha, recursive=True)
            tree_elements = tree_response.tree
            print(f"Árvore obtida. {len(tree_elements)} itens totais encontrados.")

            if tree_response.truncated:
                print(f"AVISO: A lista de arquivos do repositório foi truncada pela API.")

            arquivos_para_ler = [
                element for element in tree_elements
                if element.type == 'blob' and any(element.path.endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"Filtragem concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
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
            print(f"ERRO CRÍTICO durante a comunicação com a API: {e}")
            raise
        
        print(f"\nLeitura completa concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        return arquivos_do_repo