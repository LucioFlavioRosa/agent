from typing import Dict
from services.step_executors.base_step_executor import BaseStepExecutor
from services.step_executors.revisor_step_executor import RevisorStepExecutor
from services.step_executors.processador_step_executor import ProcessadorStepExecutor

class StepExecutorFactory:
    @staticmethod
    def create_executor(agent_type: str, job_handler) -> BaseStepExecutor:
        executors = {
            "revisor": RevisorStepExecutor,
            "processador": ProcessadorStepExecutor
        }
        
        executor_class = executors.get(agent_type)
        if not executor_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        
        return executor_class(job_handler)