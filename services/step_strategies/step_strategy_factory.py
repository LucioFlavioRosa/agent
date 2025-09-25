from typing import Dict, Any
from services.step_strategies.step_strategy_interface import IStepStrategy
from services.step_strategies.default_step_strategy import DefaultStepStrategy

class StepStrategyFactory:
    @staticmethod
    def create_strategy(step: Dict[str, Any], job_handler) -> IStepStrategy:
        strategy_type = step.get('strategy_type', 'default')
        
        if strategy_type == 'default':
            return DefaultStepStrategy(job_handler)
        
        return DefaultStepStrategy(job_handler)