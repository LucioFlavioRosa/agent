from services.step_executors.base_step_executor import BaseStepExecutor
from services.factories.llm_provider_factory import LLMProviderFactory
from agents.agente_processador import AgenteProcessador

class EpicTaskStepExecutor(BaseStepExecutor):
    def __init__(self, llm_provider_factory=None):
        self.llm_provider_factory = llm_provider_factory or LLMProviderFactory

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, agent_params):
        workflow_mode = agent_params.get('workflow_mode', job_info['data'].get('workflow_mode', 'epic_task_creation'))
        if workflow_mode != 'epic_task_creation':
            raise ValueError("EpicTaskStepExecutor só deve ser usado com workflow_mode='epic_task_creation'.")
        epic_markdown = previous_step_result.get('analysis_report') or job_info['data'].get('analysis_report')
        observacoes_usuario = agent_params.get('instrucoes_extras') or ""
        tipo_analise = step.get('params', {}).get('tipo_analise', 'criacao_epicos')
        model_name = agent_params.get('model_name')
        llm_provider = self.llm_provider_factory.create_provider(model_name, None)
        agente = AgenteProcessador(llm_provider)
        resultado = agente.main(
            tipo_analise=tipo_analise,
            repository_type=job_info['data']['repository_type'],
            instrucoes_extras=observacoes_usuario,
            usar_rag=job_info['data'].get('usar_rag', False),
            model_name=model_name,
            max_token_out=step.get('params', {}).get('max_token_out', 15000),
            workflow_mode=workflow_mode,
            job_id=job_id,
            projeto=job_info['data'].get('projeto'),
            codigo=None
        )
        return {
            "job_id": job_id,
            "step_type": "generate_epic_tasks",
            "tasks_json": resultado["resultado"]["reposta_final"],
            "step_index": current_step_index
        }
