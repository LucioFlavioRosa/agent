from typing import Dict, Any
from services.step_strategies.step_strategy_interface import IStepStrategy
from services.factories.llm_provider_factory import LLMProviderFactory
from services.step_executors.step_executor_factory import StepExecutorFactory
from tools.readers.reader_geral import ReaderGeral

class DefaultStepStrategy(IStepStrategy):
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                    current_step_index: int, previous_step_result: Dict[str, Any], 
                    repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        
        agent_type = step.get("agent_type")
        step_executor = StepExecutorFactory.create_executor(agent_type, self.job_handler)
        
        return step_executor.execute(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
    
    def should_pause_for_approval(self, step: Dict[str, Any]) -> bool:
        return step.get('requires_approval', False)
    
    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return self.job_handler.should_generate_report_only(job_info, current_step_index)