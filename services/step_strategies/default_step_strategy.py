from typing import Dict, Any

from services.step_executors.step_executor_factory import StepExecutorFactory
from tools.readers.reader_geral import ReaderGeral

class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler

    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        gerar_relatorio_apenas = job_info.get('data', {}).get('gerar_relatorio_apenas', False)
        is_first_step = current_step_index == 0
        should_finalize = gerar_relatorio_apenas and is_first_step
        if should_finalize:
            print(f"[STRATEGY] Finalizando workflow: gerar_relatorio_apenas={gerar_relatorio_apenas}, step={current_step_index}")
        return should_finalize

    def should_pause_for_approval(self, step: Dict[str, Any]) -> bool:
        return step.get('requires_approval', False)

    
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
