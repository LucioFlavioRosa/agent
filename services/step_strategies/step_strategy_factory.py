from typing import Dict, Any
from services.step_strategies.step_strategy_interface import IStepStrategy
from services.step_strategies.default_step_strategy import DefaultStepStrategy
from services.job_handler import JobHandler
from services.report_handler import ReportHandler



class StepStrategyFactory:
    @staticmethod
    # 1. A assinatura do método agora aceita 'report_handler'
    def create_strategy(step: Dict[str, Any], job_handler: JobHandler, report_handler: ReportHandler) -> IStepStrategy:
        agent_type = step.get('agent_type', 'default')
        
        # A sua lógica para escolher a classe continua a mesma
        strategies = {
            'revisor': DefaultStepStrategy,
            'processador': DefaultStepStrategy,
            'comparador': DefaultStepStrategy,
            'default': DefaultStepStrategy
        }
        
        strategy_class = strategies.get(agent_type, DefaultStepStrategy)
        
        return strategy_class(job_handler, report_handler)
