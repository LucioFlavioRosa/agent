from abc import ABC, abstractmethod

class StepStrategyInterface(ABC):
    @abstractmethod
    def execute_step(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        pass
