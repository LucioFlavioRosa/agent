from typing import Dict, Any
from services.step_executors.step_executor_factory import StepExecutorFactory
from tools.readers.reader_geral import ReaderGeral
from models import JobFields

class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                    current_step_index: int, previous_step_result: Dict[str, Any], 
                    repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        
        agent_type = step.get('agent_type')
        if not agent_type:
            raise ValueError(f"Tipo de agente não especificado na etapa {current_step_index}")
        
        executor = StepExecutorFactory.create_executor(agent_type, self.job_handler)
        
        return executor.execute(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
    
    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return job_info.get('data', {}).get(JobFields.GERAR_RELATORIO_APENAS, False) and current_step_index == 0
    
    def should_pause_for_approval(self, step: Dict[str, Any]) -> bool:
        return step.get('requires_approval', False)
