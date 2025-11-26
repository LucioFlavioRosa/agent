from mcp_azure_board.services.step_strategies.default_step_strategy import DefaultStepStrategy

class StepStrategyFactory:
    @staticmethod
    def create_strategy(step, job_handler):
        # Para este MCP, mantemos apenas a estratégia padrão
        return DefaultStepStrategy(job_handler)
