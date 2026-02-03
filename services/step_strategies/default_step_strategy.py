from typing import Dict, Any
from services.step_executors.revisor_step_executor import RevisorStepExecutor
from tools.readers.reader_geral import ReaderGeral

class DefaultStepStrategy:
    def __init__(self, job_handler):
        self.job_handler = job_handler
    
    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                    current_step_index: int, previous_step_result: Dict[str, Any], 
                    repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        # Sempre chama diretamente o RevisorStepExecutor
        executor = RevisorStepExecutor(self.job_handler)
        return executor.execute(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
    
    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return job_info.get('data', {}).get('gerar_relatorio_apenas', False) and current_step_index == 0

    def should_pause_for_approval(self, job_info: Dict[str, Any], step: Dict[str, Any]) -> bool:
        gerar_relatorio_apenas = job_info.get('data', {}).get('gerar_relatorio_apenas', False)
        result = not gerar_relatorio_apenas and step.get('requires_approval', False)
        print(f"[should_pause_for_approval] step_index=?, gerar_relatorio_apenas={gerar_relatorio_apenas}, requires_approval={step.get('requires_approval', False)}, result={result}")
        return result
