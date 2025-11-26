from services.step_executors.revisor_board_step_executor import RevisorBoardStepExecutor

class StepExecutorFactory:
    @staticmethod
    def create_executor(agent_type: str, job_handler):
        if agent_type != "revisor_board":
            raise ValueError(f"Tipo de agente não suportado neste MCP: '{agent_type}'. Apenas 'revisor_board' é permitido.")
        return RevisorBoardStepExecutor(job_handler)
