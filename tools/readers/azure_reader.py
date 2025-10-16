from typing import Dict, Optional, List, Union
from domain.interfaces.repository_provider_interface import IRepositoryProvider
from tools.azure_repository_provider import AzureRepositoryProvider
from tools.readers.base_reader import BaseReader

class AzureReader(BaseReader):
    def __init__(self, repository_provider: Optional[IRepositoryProvider] = None):
        super().__init__(repository_provider or AzureRepositoryProvider())

    def _read_azure_file(self, repositorio, caminho_arquivo: str, branch_a_ler: str) -> str:
        file_content = repositorio.get_file_content(caminho_arquivo, branch_a_ler)
        return file_content

    def _ler_arquivos_especificos(self, repositorio, branch_a_ler: str, arquivos_especificos: List[str]) -> Dict[str, str]:
        return self._ler_arquivos_especificos_base(
            repositorio, branch_a_ler, arquivos_especificos, "Azure", self._read_azure_file
        )

    def _obter_lista_todos_arquivos(self, repositorio, branch_a_ler: str) -> List[str]:
        lista_arquivos = repositorio.list_files(branch_a_ler)
        return lista_arquivos

    def _ler_repositorio_completo(self, repositorio, branch_a_ler: str, tipo_analise: str, extensoes_alvo: List[str]) -> Dict[str, str]:
        arquivos_do_repo = {}
        lista_arquivos = repositorio.list_files(branch_a_ler)
        arquivos_para_ler = [
            caminho for caminho in lista_arquivos
            if any(caminho.endswith(ext) for ext in extensoes_alvo)
        ]
        for caminho_arquivo in arquivos_para_ler:
            try:
                conteudo = repositorio.get_file_content(caminho_arquivo, branch_a_ler)
                arquivos_do_repo[caminho_arquivo] = conteudo
            except Exception:
                continue
        return arquivos_do_repo

    def read_repository_internal(
        self,
        repositorio,
        tipo_analise: str,
        nome_branch: str = None,
        arquivos_especificos: Optional[List[str]] = None,
        mapeamento_tipo_extensoes: Dict = None,
        retornar_lista_arquivos: bool = False
    ) -> Union[Dict[str, str], Dict[str, Union[Dict[str, str], List[str]]]]:
        branch_a_ler = self._validar_parametros_leitura(repositorio, nome_branch, "Azure")
        if arquivos_especificos and len(arquivos_especificos) > 0:
            arquivos_lidos = self._ler_arquivos_especificos(repositorio, branch_a_ler, arquivos_especificos)
        else:
            extensoes_alvo = self._validar_extensoes_alvo(tipo_analise, mapeamento_tipo_extensoes)
            arquivos_lidos = self._ler_repositorio_completo(repositorio, branch_a_ler, tipo_analise, extensoes_alvo)
        if retornar_lista_arquivos:
            lista_todos_arquivos = self._obter_lista_todos_arquivos(repositorio, branch_a_ler)
            return {
                'codigo': arquivos_lidos,
                'lista_arquivos': lista_todos_arquivos
            }
        else:
            return arquivos_lidos

    def read_from_cache(self, job_id: str, cache_service, retornar_lista_arquivos: bool = False) -> Optional[Dict]:
        arquivos_lidos = cache_service.get_repository_files(job_id)
        if arquivos_lidos is None:
            print(f"[AzureReader] Nenhum arquivo encontrado no cache para job_id={job_id}")
            return None
        if retornar_lista_arquivos:
            lista_arquivos = cache_service.get_file_list(job_id)
            return {
                'codigo': arquivos_lidos,
                'lista_arquivos': lista_arquivos
            }
        else:
            return arquivos_lidos
