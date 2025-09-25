from typing import Dict, Optional, List
from domain.interfaces.repository_provider_interface import IRepositoryProvider

class BaseReader:
    
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        self.repository_provider = repository_provider

    def _ler_arquivos_especificos_base(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str], platform: str, file_reader_func) -> Dict[str, str]:
        arquivos_lidos = {}
        total_arquivos = len(arquivos_especificos)
        
        print(f"Modo de leitura filtrada {platform} ativado. Lendo {total_arquivos} arquivos específicos...")
        
        for i, caminho_arquivo in enumerate(arquivos_especificos):
            try:
                print(f"  [{i+1}/{total_arquivos}] Lendo: {caminho_arquivo}")
                
                decoded_content = file_reader_func(repositorio, caminho_arquivo, branch_a_ler)
                arquivos_lidos[caminho_arquivo] = decoded_content
                
            except Exception as e:
                print(f"  [AVISO] Falha ao ler arquivo '{caminho_arquivo}': {e}. Ignorando.")
        
        print(f"Leitura filtrada {platform} concluída. {len(arquivos_lidos)} de {total_arquivos} arquivos lidos com sucesso.")
        return arquivos_lidos

    def _validar_parametros_leitura(self, repositorio, nome_branch: str, platform: str) -> str:
        if nome_branch is None:
            if hasattr(repositorio, 'default_branch'):
                branch_a_ler = repositorio.default_branch
            else:
                branch_a_ler = 'main'
            print(f"Nenhuma branch especificada. Usando a branch padrão {platform}: '{branch_a_ler}'")
        else:
            branch_a_ler = nome_branch
        return branch_a_ler

    def _validar_extensoes_alvo(self, tipo_analise: str, mapeamento_tipo_extensoes: Dict) -> List[str]:
        extensoes_alvo = mapeamento_tipo_extensoes.get(tipo_analise.lower())
        if extensoes_alvo is None:
            raise ValueError(f"Tipo de análise '{tipo_analise}' não encontrado ou não possui 'extensions' definidas em workflows.yaml")
        return extensoes_alvo