from typing import Dict
from services.step_executors.base_step_executor import BaseStepExecutor
from services.step_executors.revisor_step_executor import RevisorStepExecutor
from services.step_executors.processador_step_executor import ProcessadorStepExecutor
from services.step_executors.comparador_step_executor import ComparadorStepExecutor
from services.step_executors.epic_creation_step_executor import EpicCreationStepExecutor
from services.step_executors.epic_task_step_executor import EpicTaskStepExecutor

class StepExecutorFactory:
    @staticmethod
    def create_executor(agent_type: str, job_handler, workflow_mode: str = None) -> BaseStepExecutor:
        executors = {
            "revisor": RevisorStepExecutor,
            "processador": ProcessadorStepExecutor,
            "comparador": ComparadorStepExecutor,
            "epic_creator": EpicCreationStepExecutor
        }
        if workflow_mode == "epic_task_creation":
            return EpicTaskStepExecutor()
        executor_class = executors.get(agent_type)
        if not executor_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        if agent_type == "epic_creator":
            return executor_class()
        return executor_class(job_handler)
