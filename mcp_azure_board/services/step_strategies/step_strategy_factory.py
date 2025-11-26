from services.step_strategies.default_step_strategy import DefaultStepStrategy
from services.step_strategies.step_strategy_interface import StepStrategyInterface
from services.step_strategies.step_strategy_factory import StepStrategyFactory

class AzureBoardStepStrategyFactory(StepStrategyFactory):
    """
    Factory para criar estratégias de step específicas do MCP Azure Board.
    Pode ser estendida para incluir estratégias customizadas para Azure Board.
    """
    @staticmethod
    def create_strategy(step: dict, job_handler) -> StepStrategyInterface:
        # Para início, delega para a factory padrão (pode ser customizado depois)
        return StepStrategyFactory.create_strategy(step, job_handler)
