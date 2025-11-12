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
        
    def _get_epic_and_task_data(
        self, 
        epic_id: Optional[str] = None, 
        task_id: Optional[str] = None, 
        feature_id: Optional[str] = None
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {} 
        if epic_id:
            data['epic'] = self.azure_board_service.read_epic(epic_id)
        if feature_id:
            data['feature'] = self.azure_board_service.read_feature(feature_id)
        if task_id:
            data['task'] = self.azure_board_service.read_task(task_id)
       
        return data
    def main(
        self,
        analysis_type: Optional[str] = None,
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
        epic_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        print(f"[AgenteRevisorBoard] [DEBUG] analysis_type recebido: {analysis_type}")
        print(f"[AgenteRevisorBoard] [DEBUG] TIPO DE ANALISE={analysis_type}")
        
        print(f"[AgenteRevisorBoard] [DEBUG] Entrando no main. epic_id={epic_id}, task_id={task_id}, feature_id={feature_id}")
        if analysis_type == 'revisor_tarefas':
            if not task_id:
                raise ValueError("task_id é obrigatório quando analysis_type == 'revisor_tarefas'.")
        data = self._get_epic_and_task_data(
            epic_id=epic_id, 
            task_id=task_id, 
            feature_id=feature_id
        )
        epic_data = data.get('epic')
        feature_data = data.get('feature')
        task_data = data.get('task')
        
        instrucoes_formatadas = (instrucoes_extras or "")
        if epic_data:
            if 'error' in epic_data:
                 print(f"[AgenteRevisorBoard] AVISO: Erro ao buscar épico (contexto) '{epic_id}': {epic_data['error']}.")
            else:
                print(f"[AgenteRevisorBoard] DEBUG: Adicionando dados do Épico {epic_id} ao contexto.")
                instrucoes_formatadas += '\n\n--- DADOS DO ÉPICO (CONTEXTO) ---\n' + json.dumps(epic_data, indent=2, ensure_ascii=False)
        else:
            print(f"[AgenteRevisorBoard] DEBUG: Nenhum epic_id fornecido ou dados não encontrados. Contexto do épico pulado.")
            
        if analysis_type == 'criacao_tarefas_azure_devops':
            if not feature_id:
                raise ValueError("feature_id é obrigatório quando analysis_type == 'criacao_tarefas_azure_devops'.")
            if feature_data is None or 'error' in feature_data:
                print(f"[AgenteRevisorBoard] ERRO: Nenhum dado encontrado para a feature '{feature_id}'.")
                raise ValueError(f"Dados da feature {feature_id} não encontrados ou contêm erro: {feature_data.get('error')}")
            instrucoes_formatadas += '\n\n--- DADOS DA FEATURE (FONTE DA VERDADE) ---\n' + json.dumps(feature_data, indent=2, ensure_ascii=False)
            print(f"[AgenteRevisorBoard] DEBUG: instrucoes_formatadas final é: {instrucoes_formatadas}.")
        elif analysis_type == 'criacao_features_azure_devops':
            if not epic_id or epic_data is None or 'error' in epic_data:
                 raise ValueError(f"epic_id é obrigatório e deve ser válido para analysis_type == 'criacao_features_azure_devops'.")
        elif analysis_type == 'revisor_tarefas':
            if task_data is None or 'error' in task_data:
                print(f"[AgenteRevisorBoard] ERRO: Nenhum dado encontrado para a tarefa '{task_id}'.")
                raise ValueError(f"Dados da tarefa {task_id} não encontrados ou contêm erro: {task_data.get('error')}")
            instrucoes_formatadas += '\n\n--- DADOS DA TAREFA (FONTE DA VERDADE) ---\n' + json.dumps(task_data, indent=2, ensure_ascii=False)
            if feature_data and 'error' not in feature_data:
                instrucoes_formatadas += '\n\n--- DADOS DA FEATURE (CONTEXTO) ---\n' + json.dumps(feature_data, indent=2, ensure_ascii=False)
        if current_batch is not None and isinstance(current_batch, list) and len(current_batch) > 0:
            batch_instrucao = "ATENÇÃO: Processar APENAS os passos listados abaixo. Ignorar todos os outros passos do relatório original.\n"
            batch_instrucao += json.dumps(current_batch, indent=2, ensure_ascii=False)
            instrucoes_formatadas += "\n\n" + batch_instrucao 
        print(f"[AgenteRevisorBoard] instrucoes_extras final: {len(instrucoes_formatadas)} caracteres")
        resultado_da_ia = self.llm_provider.executar_prompt(
            tipo_tarefa=analysis_type,
            prompt_principal=None,
            instrucoes_extras=instrucoes_formatadas, 
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
            nome_repositorio=epic_id or feature_id or task_id or "ID_Nao_Fornecido", 
            tipo_analise=analysis_type,
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
