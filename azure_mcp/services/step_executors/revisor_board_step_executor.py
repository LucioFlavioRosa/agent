import logging
from azure_mcp.agents.agente_revisor_board import AgenteRevisorBoard
from models import JobFields

class RevisorBoardStepExecutor:
    def __init__(self, job_handler):
        self.job_handler = job_handler

    def execute(self, job_id, job_info, step, current_step_index, previous_step_result, repo_reader, llm_provider, agent_params):
        logging.info(f"[RevisorBoardStepExecutor] Executando step {current_step_index} para job {job_id}")
        agente = AgenteRevisorBoard(llm_provider=llm_provider)
        resultado = agente.executar(
            job_id=job_id,
            job_info=job_info,
            step=step,
            current_step_index=current_step_index,
            previous_step_result=previous_step_result,
            repo_reader=repo_reader,
            agent_params=agent_params
        )
        self.job_handler.save_step_result(job_id, current_step_index, resultado)
        return resultado
