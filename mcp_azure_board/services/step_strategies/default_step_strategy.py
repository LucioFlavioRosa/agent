from services.step_strategies.step_strategy_interface import StepStrategyInterface
from services.factories.agent_factory import AgentFactory

class DefaultStepStrategy(StepStrategyInterface):
    def __init__(self, job_handler):
        self.job_handler = job_handler

    def execute_step(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        agent_type = step.get('agent_type', step.get('agent'))
        agent = AgentFactory.create_agent(
            agent_type=agent_type,
            repository_reader=repo_reader,
            llm_provider=llm_provider
        )
        result = agent.main(
            analysis_type=job_info['data'].get('original_analysis_type'),
            instrucoes_extras=agent_params.get('instrucoes_extras', ''),
            usar_rag=agent_params.get('usar_rag', False),
            model_name=agent_params.get('model_name'),
            job_id=job_id,
            projeto=job_info['data'].get('projeto'),
            status_update=step.get('status_update'),
            usuario_executor=agent_params.get('usuario_executor'),
            current_batch=agent_params.get('current_batch'),
            task_id=agent_params.get('task_id'),
            feature_id=agent_params.get('feature_id'),
            epic_id=agent_params.get('epic_id')
        )
        return result
