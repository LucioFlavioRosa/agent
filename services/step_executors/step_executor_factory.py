from typing import Dict
from services.step_executors.base_step_executor import BaseStepExecutor
from services.step_executors.revisor_step_executor import RevisorStepExecutor
from services.step_executors.processador_step_executor import ProcessadorStepExecutor
from services.step_executors.comparador_step_executor import ComparadorStepExecutor
from services.step_executors.epic_creation_step_executor import EpicCreationStepExecutor
from services.step_executors.epic_task_step_executor import EpicTaskStepExecutor
from services.step_executors.epic_azure_devops_step_executor import EpicAzureDevOpsStepExecutor

class StepExecutorFactory:
    @staticmethod
    def create_executor(agent_type: str, job_handler, workflow_mode: str = None, dependency_container=None) -> BaseStepExecutor:
        executors = {
            "revisor": RevisorStepExecutor,
            "processador": ProcessadorStepExecutor,
            "comparador": ComparadorStepExecutor,
            "epic_creator": EpicCreationStepExecutor,
            "epic_azure_writer": EpicAzureDevOpsStepExecutor
        }
        if workflow_mode == "epic_task_creation":
            if agent_type == "epic_azure_writer":
                azure_devops_service = dependency_container.get_azure_devops_service() if dependency_container else None
                epic_parser = dependency_container.get_epic_parser() if dependency_container else None
                return EpicAzureDevOpsStepExecutor(azure_devops_service, epic_parser, job_handler)
            return EpicTaskStepExecutor()
        executor_class = executors.get(agent_type)
        if not executor_class:
            raise ValueError(f"Tipo de agente desconhecido '{agent_type}'.")
        if agent_type == "epic_creator":
            return executor_class()
        if agent_type == "epic_azure_writer":
            azure_devops_service = dependency_container.get_azure_devops_service() if dependency_container else None
            epic_parser = dependency_container.get_epic_parser() if dependency_container else None
            return executor_class(azure_devops_service, epic_parser, job_handler)
        return executor_class(job_handler)
