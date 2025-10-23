import json
from typing import Optional, Dict, Any, List
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
        if not epic_id or not organization or not project:
            raise ValueError("epic_id, organization e project são obrigatórios para leitura do épico.")
        try:
            return self.board_reader.read_epic(epic_id=epic_id, organization=organization, project=project)
        except Exception as e:
            print(f"[AgenteRevisorBoard] ERRO durante leitura do épico: {e}")
            raise RuntimeError(f"Falha ao ler o épico: {e}") from e

    def main(
        self,
        epic_id: str,
        organization: str,
        project: str,
        tipo_analise: str = None,
        instrucoes_extras: str = "",
        usar_rag: bool = False,
        model_name: Optional[str] = None,
        max_token_out: int = 15000,
        job_id: Optional[str] = None,
        projeto: Optional[str] = None,
        status_update: Optional[str] = None,
        usuario_executor: Optional[str] = None,
        current_batch: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if not epic_id:
            raise ValueError("epic_id é obrigatório para execução do agente revisor_board.")
        if not organization:
            raise ValueError("organization é obrigatório para execução do agente revisor_board.")
        if not project:
            raise ValueError("project é obrigatório para execução do agente revisor_board.")
        epic_data = self._get_epic_data(epic_id=epic_id, organization=organization, project=project)
        if not epic_data:
            print(f"[AgenteRevisorBoard] AVISO: Nenhum dado encontrado para o épico '{epic_id}'.")
            print(f"[AgenteRevisorBoard] Retornando resposta vazia devido à ausência de dados do épico")
            return {"resultado": {"reposta_final": {}}}
        epic_data_str = json.dumps(epic_data, indent=2, ensure_ascii=False)
        if current_batch is not None and isinstance(current_batch, list) and len(current_batch) > 0:
            batch_instrucao = "ATENÇÃO: Processar APENAS os passos listados abaixo. Ignorar todos os outros passos do relatório original.\n"
            batch_instrucao += json.dumps(current_batch, indent=2, ensure_ascii=False)
            if instrucoes_extras:
                instrucoes_extras += "\n\n" + batch_instrucao
            else:
                instrucoes_extras = batch_instrucao
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
            tipo_repositorio='azure_board',
            nome_repositorio=epic_id,
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
