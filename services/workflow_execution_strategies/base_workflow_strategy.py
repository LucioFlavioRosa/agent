from domain.interfaces.workflow_execution_strategy_interface import IWorkflowExecutionStrategy

class BaseWorkflowStrategy(IWorkflowExecutionStrategy):
    def __init__(self, job_handler, report_handler):
        self.job_handler = job_handler
        self.report_handler = report_handler

    def _handle_approval_pause(self, job_id, job_info, step_result, current_step_index):
        if not job_info['data'].get('report_blob_url'):
            report_text = self.report_handler.extract_report_text(step_result)
            job_info['data']['analysis_report'] = report_text
            url = self.report_handler.save_report_to_blob(job_id, job_info, report_text, report_generated_by_agent=True)
            job_info['data']['report_blob_url'] = url
            self.job_handler.update_job(job_id, job_info)
        self.job_handler.set_paused_step(job_info, current_step_index)
        self.job_handler.update_job(job_id, job_info)
