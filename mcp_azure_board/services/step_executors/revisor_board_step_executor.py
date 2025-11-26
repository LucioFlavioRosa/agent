from services.step_executors.base_step_executor import BaseStepExecutor
from agents.agente_revisor_board import AgenteRevisorBoard
from services.azure_board_service import AzureBoardService
from services.factories.llm_provider_factory import LLMProviderFactory

class RevisorBoardStepExecutor(BaseStepExecutor):
    def __init__(self, job_handler):
        super().__init__(job_handler)

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        azure_board_service = AzureBoardService(
            organization=job_info['data'].get('organization'),
            project=job_info['data'].get('project')
        )
        llm_provider = llm_provider or LLMProviderFactory.create_provider(
            agent_params.get('model_name'), None
        )
        agente = AgenteRevisorBoard(azure_board_service=azure_board_service, llm_provider=llm_provider)
        resultado = agente.main(
            analysis_type=agent_params.get('analysis_type'),
            instrucoes_extras=agent_params.get('instrucoes_extras', ''),
            usar_rag=agent_params.get('usar_rag', False),
            model_name=agent_params.get('model_name'),
            max_token_out=agent_params.get('max_token_out', 15000),
            job_id=agent_params.get('job_id'),
            projeto=agent_params.get('projeto'),
            status_update=agent_params.get('status_update'),
            usuario_executor=agent_params.get('usuario_executor'),
            current_batch=agent_params.get('current_batch'),
            task_id=agent_params.get('task_id'),
            feature_id=agent_params.get('feature_id'),
            epic_id=agent_params.get('epic_id')
        )
        return resultado
