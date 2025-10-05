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
        gerar_relatorio_apenas = job_info.get('data', {}).get(JobFields.GERAR_RELATORIO_APENAS, False)
        analysis_report = job_info.get('data', {}).get(JobFields.ANALYSIS_REPORT)
        blob_url = job_info.get('data', {}).get(JobFields.REPORT_BLOB_URL)
        print(f"[STRATEGY] Verificando finalização - gerar_relatorio_apenas: {gerar_relatorio_apenas}, current_step: {current_step_index}, report_exists: {bool(analysis_report)}, blob_url_exists: {bool(blob_url)}")
        if gerar_relatorio_apenas and current_step_index == 0:
            if analysis_report and blob_url:
                return True
            else:
                print(f"[STRATEGY] Não pode finalizar: relatório não existe ainda")
                return False
        return False
    
    def should_pause_for_approval(self, step: Dict[str, Any]) -> bool:
        return step.get('requires_approval', False)
