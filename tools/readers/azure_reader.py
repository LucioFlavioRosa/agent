from typing import Dict, Optional, List, Union
from tools.readers.base_reader import BaseReader
from tools.azure_repository_provider import AzureRepositoryProvider
from domain.interfaces.repository_provider_interface import IRepositoryProvider

class AzureReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or AzureRepositoryProvider())

    # --- INÍCIO DA CORREÇÃO 1: Adicionando o método faltante ---
    def _obter_lista_todos_arquivos(self, repositorio, nome_branch: str) -> List[str]:
        """Obtém a lista completa de caminhos de arquivos de uma branch."""
        print(f"[Azure Reader] Obtendo árvore de arquivos da branch '{nome_branch}' para listagem...")
        items = repositorio.get_items(nome_branch)
        print(f"[Azure Reader] Árvore obtida. {len(items)} itens totais encontrados.")
        return [item['path'] for item in items if item.get('isFolder') is not True]
    # --- FIM DA CORREÇÃO 1 ---

    # --- INÍCIO DA CORREÇÃO 2: Renomeando o método ---
    def read_repository_internal(
        self,
        repositorio,
        tipo_analise: str,
        nome_branch: Optional[str] = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None
    ) -> Dict[str, str]:
    # --- FIM DA CORREÇÃO 2 ---
        
        branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "Azure")
        
        # A lógica para obter todos os itens já está no novo método, mas podemos otimizar depois.
        # Por enquanto, vamos manter a lógica original para garantir o funcionamento.
        print(f"[Azure Reader] Obtendo árvore de arquivos da branch '{branch_a_ler}'...")
        items = repositorio.get_items(branch_a_ler)
        print(f"[Azure Reader] Árvore obtida. {len(items)} itens totais encontrados.")
        
        if arquivos_especificos and len(arquivos_especificos) > 0:
            print(f"[Azure Reader] Filtrando por {len(arquivos_especificos)} arquivos específicos.")
            items_to_read = [item for item in items if item['path'] in arquivos_especificos]
        else:
            extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
            print(f"[Azure Reader] Filtrando por extensões: {extensoes_alvo}") # Log adicionado para clareza
            items_to_read = [item for item in items if any(item['path'].endswith(ext) for ext in extensoes_alvo)]
            
        print(f"[Azure Reader] {len(items_to_read)} arquivos selecionados para leitura de conteúdo.")
        
        arquivos_do_repo = {}
        for item in items_to_read:
            try:
                conteudo = repositorio.get_file_content(item['path'], branch_a_ler)
                arquivos_do_repo[item['path']] = conteudo
                print(f"[Azure Reader] Conteúdo de '{item['path']}' lido com sucesso.")
            except Exception as e:
                print(f"[Azure Reader] AVISO: Falha ao ler conteúdo de '{item['path']}'. Erro: {e}")

        # A lógica de retornar a lista de arquivos agora é tratada pela classe BaseReader,
        # então podemos remover essa parte daqui para simplificar.
        return arquivos_do_repo
