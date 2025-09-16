import json
from typing import Dict, Any
from domain.interfaces.approval_handler_interface import IApprovalHandler
from domain.interfaces.job_manager_interface import IJobManager
from domain.interfaces.report_manager_interface import IReportManager

class ApprovalHandler(IApprovalHandler):
    def __init__(self, job_manager: IJobManager, report_manager: IReportManager):
        self.job_manager = job_manager
        self.report_manager = report_manager
    
    def handle_approval_step(self, job_id: str, job_info: Dict[str, Any], step_index: int, step_result: Dict[str, Any]) -> None:
        print(f"[{job_id}] Etapa requer aprovação.")

        report_text = step_result.get("relatorio", json.dumps(step_result, indent=2, ensure_ascii=False))
        job_info['data']['analysis_report'] = report_text

        if job_info['data'].get('gerar_novo_relatorio', True):
            self.report_manager.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
        else:
            print(f"[{job_id}] gerar_novo_relatorio=False - Não salvando relatório no Blob Storage")

        job_info['status'] = 'pending_approval'
        job_info['data']['paused_at_step'] = step_index
        self.job_manager.update_job(job_id, job_info)