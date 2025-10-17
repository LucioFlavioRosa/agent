from services.job_handler import JobHandler
from typing import Dict, Any
from services.step_executors.step_executor_factory import StepExecutorFactory
from services.step_strategies.step_strategy_interface import IStepStrategy
from tools.readers.reader_geral import ReaderGeral
from services.report_handler import ReportHandler

class DefaultStepStrategy:
    def __init__(self, job_handler: JobHandler, report_handler: ReportHandler):
        self.job_handler = job_handler
        self.report_handler = report_handler
    
    def execute_step(self, job_id: str, job_info: Dict[str, Any], step: Dict[str, Any], 
                     current_step_index: int, previous_step_result: Dict[str, Any], 
                     repo_reader: ReaderGeral, llm_provider, agent_params: Dict[str, Any]) -> Dict[str, Any]:
        
        agent_type = step.get('agent_type')
        if not agent_type:
            raise ValueError(f"Tipo de agente não especificado na etapa {current_step_index}")
        
        executor = StepExecutorFactory.create_executor(agent_type, self.job_handler)
        result = executor.execute(
            job_id, job_info, step, current_step_index, 
            previous_step_result, repo_reader, llm_provider, agent_params
        )
        
        if current_step_index == 0:
            report_text = ReportHandler.extract_report_text(result)
            if report_text and isinstance(report_text, str) and report_text.strip():
                url = self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
                job_info['data']['report_blob_url'] = url
                job_info['data']['analysis_report'] = report_text
                self.job_handler.update_job(job_id, job_info)
                
        return result
    
    def should_finalize_workflow(self, job_info: Dict[str, Any], current_step_index: int) -> bool:
        return job_info.get('data', {}).get('gerar_relatorio_apenas', False) and current_step_index == 0

    def should_pause_for_approval(self, job_info: Dict[str, Any], step: Dict[str, Any]) -> bool:
        gerar_relatorio_apenas = job_info.get('data', {}).get('gerar_relatorio_apenas', False)
        result = not gerar_relatorio_apenas and step.get('requires_approval', False)
        print(f"[should_pause_for_approval] step_index=?, gerar_relatorio_apenas={gerar_relatorio_apenas}, requires_approval={step.get('requires_approval', False)}, result={result}")
        return result
