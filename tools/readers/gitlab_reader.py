import base64
from typing import Dict, Optional, List
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.gitlab_repository_provider import GitLabRepositoryProvider

class GitLabReader:
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        self.repository_provider = repository_provider or GitLabRepositoryProvider()

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
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

    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
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

    def read_repository_internal(
        self, 
        repositorio, 
        tipo_analise: str, 
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
        if nome_branch is None:
            if hasattr(repositorio, 'default_branch'):
                branch_a_ler = repositorio.default_branch
            else:
                branch_a_ler = 'main'
            print(f"Nenhuma branch especificada. Usando a branch padrão GitLab: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"Modo de leitura filtrada GitLab ativado para {len(arquivos_especificos)} arquivos específicos.")
            return self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            print("Modo de leitura completa GitLab ativado (filtro por extensão).")
            extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
            if extensoes_alvo is None:
                raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")
            return self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)