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
        
        print(f"[Azure Reader] Modo de leitura filtrada Azure DevOps ativado. Lendo {total_arquivos} arquivos específicos...")
        
        organization = repositorio_dict.get('_organization')
        project = repositorio_dict.get('_project')
        repository = repositorio_dict.get('_repository')
        
        print(f"[Azure Reader] Organização: {organization}, Projeto: {project}, Repositório: {repository}")
        
        headers = self._get_azure_auth_headers(repositorio_dict)
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
        
        print(f"[Azure Reader] Base URL construída: {base_url}")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                print(f"[Azure Reader] [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                url = f"{base_url}/items?path={caminho_arquivo}&includeContent=true&versionDescriptor.version={branch_a_ler}&api-version=7.0"
                print(f"[Azure Reader] URL da requisição: {url}")
                
                response = requests.get(url, headers=headers, timeout=30)
                
                print(f"[Azure Reader] Status da resposta: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"[Azure Reader] Resposta JSON recebida para {caminho_arquivo}")
                    
                    if 'content' not in data:
                        print(f"[Azure Reader] AVISO: Chave 'content' não encontrada na resposta. JSON completo: {data}")
                        continue
                    
                    content = data.get('content', '')
                    if content:
                        arquivos_lidos[caminho_arquivo] = content
                        print(f"[Azure Reader] Arquivo {caminho_arquivo} lido com sucesso ({len(content)} caracteres)")
                    else:
                        print(f"[Azure Reader] AVISO: Conteúdo vazio para arquivo {caminho_arquivo}")
                else:
                    print(f"[Azure Reader] AVISO: Arquivo '{caminho_arquivo}' não encontrado ou inacessível (status: {response.status_code})")
                    if response.text:
                        print(f"[Azure Reader] Corpo da resposta de erro: {response.text}")
                    
            except Exception as e:
                print(f"[Azure Reader] ERRO: Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"[Azure Reader] Leitura filtrada Azure DevOps concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        print(f"[Azure Reader] Arquivos lidos: {list(arquivos_lidos.keys())}")
        
        return arquivos_lidos

    def _ler_repositorio_completo(self, repositorio_dict: dict, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        
        organization = repositorio_dict.get('_organization')
        project = repositorio_dict.get('_project')
        repository = repositorio_dict.get('_repository')
        
        print(f"[Azure Reader] Leitura completa - Organização: {organization}, Projeto: {project}, Repositório: {repository}")
        print(f"[Azure Reader] Extensões alvo para análise '{tipo_analise}': {extensoes_alvo}")
        
        headers = self._get_azure_auth_headers(repositorio_dict)
        base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
        
        print(f"[Azure Reader] Base URL construída: {base_url}")
        
        try:
            print(f"[Azure Reader] Obtendo árvore de arquivos Azure DevOps da branch '{branch_a_ler}'...")
            
            items_url = f"{base_url}/items?recursionLevel=Full&versionDescriptor.version={branch_a_ler}&api-version=7.0"
            print(f"[Azure Reader] URL da árvore de arquivos: {items_url}")
            
            response = requests.get(items_url, headers=headers, timeout=30)
            
            print(f"[Azure Reader] Status da resposta da árvore: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[Azure Reader] ERRO: Falha ao obter lista de arquivos. Corpo da resposta: {response.text}")
                raise Exception(f"Erro ao obter lista de arquivos: {response.status_code} - {response.text}")
            
            items_data = response.json()
            all_items = items_data.get('value', [])
            
            print(f"[Azure Reader] Árvore Azure DevOps obtida. {len(all_items)} itens totais encontrados.")
            
            if not all_items:
                print(f"[Azure Reader] AVISO CRÍTICO: Lista de itens vazia. JSON completo da resposta: {items_data}")
            
            arquivos_para_ler = [
                item for item in all_items
                if not item.get('isFolder', True) and any(item.get('path', '').endswith(ext) for ext in extensoes_alvo)
            ]
            
            print(f"[Azure Reader] Filtragem Azure DevOps concluída. {len(arquivos_para_ler)} arquivos com as extensões {extensoes_alvo} serão lidos.")
            
            if not arquivos_para_ler:
                print(f"[Azure Reader] AVISO CRÍTICO: Nenhum arquivo encontrado com as extensões especificadas.")
                print(f"[Azure Reader] Todos os itens encontrados: {[item.get('path') for item in all_items if not item.get('isFolder', True)]}")
            
            for i, item in enumerate(arquivos_para_ler):
                if (i + 1) % 50 == 0:
                    print(f"[Azure Reader] ...lendo arquivo {i + 1} de {len(arquivos_para_ler)} ({item.get('path')})")
                
                try:
                    file_path = item.get('path')
                    content_url = f"{base_url}/items?path={file_path}&includeContent=true&versionDescriptor.version={branch_a_ler}&api-version=7.0"
                    
                    content_response = requests.get(content_url, headers=headers, timeout=30)
                    
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        
                        if 'content' not in content_data:
                            print(f"[Azure Reader] AVISO: Chave 'content' não encontrada para arquivo '{file_path}'. JSON completo: {content_data}")
                            continue
                        
                        file_content = content_data.get('content', '')
                        if file_content:
                            arquivos_do_repo[file_path] = file_content
                        else:
                            print(f"[Azure Reader] AVISO: Conteúdo vazio para arquivo '{file_path}'")
                    else:
                        print(f"[Azure Reader] AVISO: Falha ao ler conteúdo do arquivo '{file_path}' (status: {content_response.status_code})")
                        if content_response.text:
                            print(f"[Azure Reader] Corpo da resposta de erro: {content_response.text}")
                        
                except Exception as e:
                    print(f"[Azure Reader] AVISO: Falha ao ler ou decodificar o conteúdo do arquivo '{item.get('path')}'. Pulando. Erro: {e}")

        except Exception as e:
            print(f"[Azure Reader] ERRO CRÍTICO durante a comunicação com a API Azure DevOps: {e}")
            raise
        
        print(f"[Azure Reader] Leitura completa Azure DevOps concluída. Total de {len(arquivos_do_repo)} arquivos lidos e processados.")
        print(f"[Azure Reader] Arquivos lidos: {list(arquivos_do_repo.keys())}")
        
        return arquivos_do_repo

    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        print(f"[Azure Reader] Iniciando leitura interna - Tipo análise: {tipo_analise}")
        print(f"[Azure Reader] Repositório recebido: {type(repositorio)} - {repositorio}")
        
        if nome_branch is None:
            if isinstance(repositorio, dict) and 'default_branch' in repositorio:
                branch_a_ler = repositorio['default_branch']
            else:
                branch_a_ler = 'main'
            print(f"[Azure Reader] Nenhuma branch especificada. Usando a branch padrão Azure: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        print(f"[Azure Reader] Branch a ser lida: {branch_a_ler}")
        
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"[Azure Reader] Modo de leitura filtrada Azure DevOps ativado para {len(arquivos_especificos)} arquivos específicos.")
            resultado = self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print(f"[Azure Reader] Modo de leitura completa Azure DevOps ativado (filtro por extensão).")
            print(f"[Azure Reader] Mapeamento de extensões recebido: {mapeamento_tipo_extensoes}")
            
            extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
            if extensoes_alvo is None:
                print(f"[Azure Reader] ERRO: Tipo de análise '{tipo_analise}' não encontrado no mapeamento")
                raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")
            
            print(f"[Azure Reader] Extensões alvo obtidas: {extensoes_alvo}")
            resultado = self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)
        
        print(f"[Azure Reader] Resultado final da leitura: {len(resultado)} arquivos")
        if not resultado:
            print(f"[Azure Reader] AVISO CRÍTICO: Nenhum arquivo foi lido do repositório Azure DevOps")
        
        return resultado