import json
from typing import Optional, Dict, Any, List
from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider

class AgenteRevisor:
    
    def __init__(
        self,
        repository_reader: IRepositoryReader,
        llm_provider: ILLMProvider
    ):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str,
        repository_type: str,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        try:
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"Iniciando a leitura filtrada do repositório: {repositorio}, branch: {nome_branch}, tipo: {repository_type}")
                print(f"Arquivos específicos solicitados: {len(arquivos_especificos)} arquivos")
            else:
                print(f"Iniciando a leitura completa do repositório: {repositorio}, branch: {nome_branch}, tipo: {repository_type}")
            
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos
            )
            
            return codigo_para_analise
            
        except Exception as e:
            raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

    def main(
        self,
        tipo_analise: str,
        repositorio: str,
        repository_type: str,
        nome_branch: Optional[str] = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        codigo_para_analise = self._get_code(
            repositorio=repositorio,
            nome_branch=nome_branch,
            tipo_analise=tipo_analise,
            repository_type=repository_type,
            arquivos_especificos=arquivos_especificos
        )

        if not codigo_para_analise:
            if arquivos_especificos and len(arquivos_especificos) > 0:
                print(f"AVISO: Nenhum dos arquivos específicos foi encontrado no repositório para a análise '{tipo_analise}'.")
            else:
                print(f"AVISO: Nenhum código encontrado no repositório para a análise '{tipo_analise}'.")
            return {"resultado": {"reposta_final": {}}}

        codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)

        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out
        )

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }