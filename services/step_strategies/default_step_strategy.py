from typing import Dict, Any
from models import JobFields

from services.step_executors.step_executor_factory import StepExecutorFactory
from tools.readers.reader_geral import ReaderGeral

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

    def should_finalize_workflow(self, job_info, current_step_index):
        gerar_relatorio_apenas = job_info.get('data', {}).get(JobFields.GERAR_RELATORIO_APENAS)
        debug_msg = f"[DEBUG] should_finalize_workflow: job_id={job_info.get('job_id', 'N/A')}, current_step_index={current_step_index}, gerar_relatorio_apenas={gerar_relatorio_apenas}"
        print(debug_msg)
        return current_step_index == 0 and gerar_relatorio_apenas is True

    def should_pause_for_approval(self, step):
        return step.get('pause_for_approval', False)
