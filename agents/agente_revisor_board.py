import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from domain.interfaces.board_reader_interface import IBoardReader
from domain.interfaces.llm_provider_interface import ILLMProvider
from agents.logging_utils import init_logger, log_custom_data

class AgenteRevisorBoard:
    def __init__(self, board_reader: IBoardReader, llm_provider: ILLMProvider):
        self.board_reader = board_reader
        self.llm_provider = llm_provider
        init_logger()

    def _get_epic_data(self, epic_id: str, organization: str, project: str) -> Dict[str, Any]:
        return self.board_reader.read_epic(epic_id=epic_id, organization=organization, project=project)

    def main(
        self,
        tipo_analise: str,
        epic_id: str,
        organization: str,
        project: str,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        job_id: Optional[str] = None,
        projeto: Optional[str] = None,
        status_update: Optional[str] = None,
        usuario_executor: Optional[str] = None,
        current_batch: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        epic_data = self._get_epic_data(epic_id=epic_id, organization=organization, project=project)
        if not epic_data:
            return {"resultado": {"reposta_final": {}}}
        epic_data_str = json.dumps(epic_data, indent=2, ensure_ascii=False)
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=epic_data_str,
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
            tipo_repositorio=None,
            nome_repositorio=None,
            tipo_analise=tipo_analise,
            model_name=model_name,
            modo_adicao_incremental=False,
            usuario_executor=usuario_executor
        )
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }
