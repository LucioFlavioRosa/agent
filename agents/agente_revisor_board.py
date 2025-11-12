import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from domain.interfaces.llm_provider_interface import ILLMProvider
from agents.logging_utils import init_logger, log_custom_data
from services.azure_board_service import AzureBoardService

class AgenteRevisorBoard:
    def __init__(self, azure_board_service: AzureBoardService, llm_provider: ILLMProvider):
        self.azure_board_service = azure_board_service
        self.llm_provider = llm_provider
        init_logger()

    def _get_epic_and_task_data(self, epic_id: str, task_id: Optional[str] = None, feature_id: Optional[str] = None) -> Dict[str, Any]:
        print(f"[AgenteRevisorBoard] [DEBUG] Entrando no main. epic_id={epic_id}, task_id={task_id}, feature_id={feature_id}")
        if not epic_id:
            raise ValueError("epic_id é obrigatório para leitura do épico.")
        epic_data = self.azure_board_service.read_epic(epic_id)
        result = {'epic': epic_data}
        if task_id:
            task_data = self.azure_board_service.read_task(task_id)
            result['task'] = task_data
        if feature_id:
            feature_data = self.azure_board_service.read_feature(feature_id)
            result['feature'] = feature_data
        return result

    def main(
        self,
        epic_id: str,
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
        task_id: Optional[str] = None,
        feature_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        print(f"[AgenteRevisorBoard] [DEBUG] Entrando no main. epic_id={epic_id}, task_id={task_id}, feature_id={feature_id}")
        if not epic_id:
            raise ValueError("epic_id é obrigatório para execução do agente revisor_board.")
        if tipo_analise == 'revisor_tarefas':
            if not task_id:
                raise ValueError("task_id é obrigatório quando analysis_type == 'revisor_tarefas'.")
        if tipo_analise == 'criacao_tarefas_azure_devops':
            if not feature_id:
                raise ValueError("feature_id é obrigatório quando analysis_type == 'criacao_tarefas_azure_devops'.")
        data = self._get_epic_and_task_data(epic_id=epic_id, task_id=task_id, feature_id=feature_id)
        epic_data = data.get('epic')
        task_data = data.get('task')
        feature_data = data.get('feature')
        if tipo_analise == 'criacao_features_azure_devops':
            if epic_data is None:
                print(f"[AgenteRevisorBoard] AVISO: Nenhum dado encontrado para o épico '{epic_id}'.")
                print(f"[AgenteRevisorBoard] Retornando resposta vazia devido à ausência de dados do épico")
                return {"resultado": {"reposta_final": {}}}
            instrucoes_extras = (instrucoes_extras or "") + '\n\n--- DADOS DO ÉPICO ---\n' + json.dumps(epic_data, indent=2, ensure_ascii=False)
        elif tipo_analise == 'criacao_tarefas_azure_devops':
            if epic_data is None:
                print(f"[AgenteRevisorBoard] AVISO: Nenhum dado encontrado para o épico '{epic_id}'.")
                print(f"[AgenteRevisorBoard] Retornando resposta vazia devido à ausência de dados do épico")
                return {"resultado": {"reposta_final": {}}}
            if feature_data is None:
                print(f"[AgenteRevisorBoard] AVISO: Nenhum dado encontrado para a feature '{feature_id}'.")
                print(f"[AgenteRevisorBoard] Retornando resposta vazia devido à ausência de dados da feature")
                return {"resultado": {"reposta_final": {}}}
            instrucoes_extras = (instrucoes_extras or "") + '\n\n--- DADOS DO ÉPICO ---\n' + json.dumps(epic_data, indent=2, ensure_ascii=False) + '\n\n--- DADOS DA FEATURE ---\n' + json.dumps(feature_data, indent=2, ensure_ascii=False)
        else:
            if epic_data is None:
                print(f"[AgenteRevisorBoard] AVISO: Nenhum dado encontrado para o épico '{epic_id}'.")
                print(f"[AgenteRevisorBoard] Retornando resposta vazia devido à ausência de dados do épico")
                return {"resultado": {"reposta_final": {}}}
            if task_data is not None:
                print(f"[AgenteRevisorBoard] Dados da tarefa obtidos: {len(json.dumps(task_data))} caracteres")
                instrucoes_extras = (instrucoes_extras or "") + '\n\n--- DADOS DO ÉPICO ---\n' + json.dumps(epic_data, indent=2, ensure_ascii=False) + '\n\n--- DADOS DA TAREFA ---\n' + json.dumps(task_data, indent=2, ensure_ascii=False)
            else:
                instrucoes_extras = (instrucoes_extras or "") + '\n\n--- DADOS DO ÉPICO ---\n' + json.dumps(epic_data, indent=2, ensure_ascii=False)
        if current_batch is not None and isinstance(current_batch, list) and len(current_batch) > 0:
            batch_instrucao = "ATENÇÃO: Processar APENAS os passos listados abaixo. Ignorar todos os outros passos do relatório original.\n"
            batch_instrucao += json.dumps(current_batch, indent=2, ensure_ascii=False)
            if instrucoes_extras:
                instrucoes_extras += "\n\n" + batch_instrucao
            else:
                instrucoes_extras = batch_instrucao
        print(f"[AgenteRevisorBoard] instrucoes_extras final: {len(instrucoes_extras)} caracteres")
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=tipo_analise,
            prompt_principal=None,
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
        if not isinstance(resultado_da_ia, dict) or 'reposta_final' not in resultado_da_ia or not resultado_da_ia['reposta_final']:
            raise ValueError(f"[AgenteRevisorBoard] ERRO: A resposta da LLM está vazia ou malformada. resultado_da_ia: {resultado_da_ia}")
        return {
            "resultado": {
                "reposta_final": resultado_da_ia
            }
        }
