from typing import Dict, Any
from services.step_strategies.default_step_strategy import DefaultStepStrategy

class StepStrategyFactory:
    @staticmethod
    def create_strategy(step: Dict[str, Any], job_handler):
        agent_type = step.get('agent_type', 'default')
        
        strategies = {
            'revisor': DefaultStepStrategy,
            'processador': DefaultStepStrategy,
            'comparador': DefaultStepStrategy,
            'default': DefaultStepStrategy
        }
        
        strategy_class = strategies.get(agent_type, DefaultStepStrategy)
        return strategy_class(job_handler)