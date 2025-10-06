class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler

    def execute_step(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        return llm_provider.execute_agent(
            job_id=job_id,
            job_info=job_info,
            step=step,
            current_step_index=current_step_index,
            previous_step_result=previous_step_result,
            repo_reader=repo_reader,
            agent_params=agent_params
        )

    def should_finalize_workflow(self, job_info, current_step_index):
        return (job_info.get('data', {}).get('gerar_relatorio_apenas') is True and current_step_index == 0)

    def should_pause_for_approval(self, step):
        return step.get('pause_for_approval', False)
