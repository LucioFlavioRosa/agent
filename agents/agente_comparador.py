import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from domain.interfaces.repository_reader_interface import IRepositoryReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from agents.logging_utils import init_logger, log_custom_data

class AgenteComparador:

    def __init__(
        self,
        repository_reader: IRepositoryReader,
        llm_provider: ILLMProvider
    ):
        self.repository_reader = repository_reader
        self.llm_provider = llm_provider
        init_logger()

    def _get_code(
        self,
        repositorio: str,
        nome_branch: Optional[str],
        tipo_analise: str,
        repository_type: str,
        arquivos_especificos: Optional[List[str]] = None
    ) -> Dict[str, str]:
        try:
            codigo_para_analise = self.repository_reader.read_repository(
                nome_repo=repositorio,
                tipo_analise=tipo_analise,
                repository_type=repository_type,
                nome_branch=nome_branch,
                arquivos_especificos=arquivos_especificos
            )
                
            return codigo_para_analise
            
        except Exception as e:
            print(f"[Agente Comparador] ERRO durante leitura do repositório {repositorio}: {e}")
            raise RuntimeError(f"Falha ao ler o repositório {repositorio}: {e}") from e

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
        arquivos_especificos: Optional[List[str]] = None,
        job_id: Optional[str] = None,
        projeto: Optional[str] = None,
        status_update: Optional[str] = None,
        repo_name_modernizado: Optional[str] = None,
        branch_name_modernizado: Optional[str] = None,
        repo_name_original: Optional[str] = None,
        branch_name_original: Optional[str] = None
    ) -> Dict[str, Any]:

        log_custom_data(
            job_id=job_id,
            projeto=projeto,
            data_hora=datetime.now(timezone.utc).isoformat(),
            status="INICIADO",
            tipo_repositorio=repository_type,
            nome_repositorio=repositorio,
            tipo_analise=tipo_analise,
            model_name=model_name,
            repo_modernizado=repo_name_modernizado,
            repo_original=repo_name_original
        )

        codigo_modernizado = {}
        codigo_original = {}

        if repo_name_modernizado:
            print(f"[Agente Comparador] Lendo repositório modernizado: {repo_name_modernizado}")
            codigo_modernizado = self._get_code(
                repositorio=repo_name_modernizado,
                nome_branch=branch_name_modernizado,
                tipo_analise=tipo_analise,
                repository_type=repository_type,
                arquivos_especificos=arquivos_especificos
            )

        if repo_name_original:
            print(f"[Agente Comparador] Lendo repositório original: {repo_name_original}")
            codigo_original = self._get_code(
                repositorio=repo_name_original,
                nome_branch=branch_name_original,
                tipo_analise=tipo_analise,
                repository_type=repository_type,
                arquivos_especificos=arquivos_especificos
            )

        if not codigo_modernizado and not codigo_original:
            print(f"[Agente Comparador] AVISO: Nenhum código encontrado em ambos os repositórios para a análise '{tipo_analise}'.")
            
            log_custom_data(
                job_id=job_id,
                projeto=projeto,
                status="ERRO_SEM_CODIGO",
                tipo_analise=tipo_analise,
                data_hora=datetime.now(timezone.utc).isoformat()
            )
            
            return {"resultado": {"reposta_final": {}}}

        dados_comparacao = {
            "codigo_modernizado": codigo_modernizado,
            "codigo_original": codigo_original,
            "repositorio_modernizado": repo_name_modernizado,
            "repositorio_original": repo_name_original,
            "branch_modernizada": branch_name_modernizado,
            "branch_original": branch_name_original
        }

        codigo_str = json.dumps(dados_comparacao, indent=2, ensure_ascii=False)

        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=codigo_str,
            instrucoes_extras=instrucoes_extras,
            usar_rag=usar_rag,
            model_name=model_name,
            max_token_out=max_token_out,
        )

        log_custom_data(
            job_id=job_id,
            projeto=projeto,
            data_hora=datetime.now(timezone.utc).isoformat(),
            tokens_in=resultado_da_ia['tokens_entrada'],
            tokens_out=resultado_da_ia['tokens_saida'],
            status='FINALIZADO',
            tipo_repositorio=repository_type,
            nome_repositorio=repositorio,
            tipo_analise=tipo_analise,
            model_name=model_name,
            repo_modernizado=repo_name_modernizado,
            repo_original=repo_name_original
        )

        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }