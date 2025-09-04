import requests
from typing import Dict, Optional, List
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.conectores.azure_conector import AzureConector

class AzureReader:
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        self.repository_provider = repository_provider or AzureRepositoryProvider()

    def _get_azure_auth_headers(self, repositorio_dict: dict) -> dict:
        connector = AzureConector.create_with_defaults()
        organization = repositorio_dict.get('_organization')
        token = connector._get_token_for_org(organization)
        
        import base64
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }

    def _ler_arquivos_especificos(self, repositorio_dict: dict, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
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

    def _ler_repositorio_completo(self, repositorio_dict: dict, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
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

    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        if nome_branch is None:
            if isinstance(repositorio, dict) and 'default_branch' in repositorio:
                branch_a_ler = repositorio['default_branch']
            else:
                branch_a_ler = 'main'
            print(f"Nenhuma branch especificada. Usando a branch padrão Azure: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada Azure DevOps ativado para {len(arquivos_especificos)} arquivos específicos.")
            return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa Azure DevOps ativado (filtro por extensão).")
            extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
            if extensoes_alvo is None:
                raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")
            return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)