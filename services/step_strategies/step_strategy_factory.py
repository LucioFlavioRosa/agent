from typing import Dict
from services.step_strategies.default_step_strategy import DefaultStepStrategy
from services.step_strategies.step_strategy_interface import IStepStrategy
from services.step_strategies.step_strategy_factory import StepStrategyFactory as _StepStrategyFactory
from services.job_handler import JobHandler

class StepStrategyFactory:
    @staticmethod
    def create_strategy(step: Dict, job_handler: JobHandler) -> IStepStrategy:
        step_type = step.get('step_type') or step.get('tipo_analise')
        # Para os novos tipos, usamos a estratégia padrão (pode ser extendido no futuro)
        if step_type in [
            'GENERATE_TASKS', 'CREATE_EPIC_AND_TASKS',
            'GENERATE_REPORT', 'COMMIT_CODE', 'GENERATE_CODE'
        ]:
            return DefaultStepStrategy(job_handler)
        # Fallback para tipos antigos ou não especificados
        return DefaultStepStrategy(job_handler)
