class BaseStepExecutor:
    def __init__(self, job_handler):
        self.job_handler = job_handler

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        raise NotImplementedError("Método execute deve ser implementado pelas subclasses.")
