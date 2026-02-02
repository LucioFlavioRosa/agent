from services.step_executors.base_step_executor import BaseStepExecutor
from services.step_executors.comparador_step_executor import ComparadorStepExecutor
from services.step_executors.revisor_step_executor import RevisorStepExecutor

def get_step_executor(step_type: str, job_handler) -> BaseStepExecutor:
    """
    Factory para instanciar o executor correto para cada tipo de agente.
    Removido suporte ao ProcessadorStepExecutor conforme reestruturação do projeto.
    """
    if step_type == "comparador":
        return ComparadorStepExecutor(job_handler)
    elif step_type == "revisor":
        return RevisorStepExecutor(job_handler)
    else:
        raise ValueError(f"Executor de step não encontrado para o tipo: {step_type}")
