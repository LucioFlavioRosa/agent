from mcp_azure_board.services.step_executors.step_executor_factory import StepExecutorFactory

class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler
    def execute_step(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        agent_type = step.get('agent_type', step.get('agent'))
        executor = StepExecutorFactory.create_executor(agent_type, self.job_handler)
        return executor.execute(
            job_id=job_id,
            job_info=job_info,
            step=step,
            current_step_index=current_step_index,
            previous_step_result=previous_step_result,
            llm_provider=llm_provider,
            agent_params=agent_params
        )
