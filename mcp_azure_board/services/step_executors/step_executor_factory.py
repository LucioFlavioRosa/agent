from services.step_executors.revisor_board_step_executor import RevisorBoardStepExecutor
from services.step_executors.base_step_executor import BaseStepExecutor

class StepExecutorFactory:
    @staticmethod
    def create_executor(agent_type: str, job_handler) -> BaseStepExecutor:
        executors = {
            "revisor_board": RevisorBoardStepExecutor
        }
        executor_class = executors.get(agent_type)
        if not executor_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        return executor_class(job_handler)
