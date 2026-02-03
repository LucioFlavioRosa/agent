from typing import Any, Dict

VALID_AGENT_TYPES = ['processador']

class SimplifiedWorkflowService:
    def __init__(self):
        self.jobs = {}
        self.reports = {}

    def start_analysis(self, payload: Any) -> str:
        analysis_type = getattr(payload, 'analysis_type', None)
        if analysis_type not in VALID_AGENT_TYPES:
            raise ValueError(f"Tipo de agente inválido: {analysis_type}. Apenas 'processador' é permitido.")
        job_id = f"job_{len(self.jobs)+1}"
        self.jobs[job_id] = {
            'status': 'started',
            'repository_type': getattr(payload, 'repository_type', None),
            'repo_name': getattr(payload, 'repo_name', None),
            'branch_name': getattr(payload, 'branch_name', None),
            'analysis_type': analysis_type,
            'arquivos_especificos': getattr(payload, 'arquivos_especificos', None),
            'instrucoes_extras': getattr(payload, 'instrucoes_extras', None),
            'projeto': getattr(payload, 'projeto', None),
            'analysis_name': getattr(payload, 'analysis_name', None),
            'gerar_relatorio_apenas': getattr(payload, 'gerar_relatorio_apenas', None),
            'retornar_lista_arquivos': getattr(payload, 'retornar_lista_arquivos', None),
            'usuario_executor': getattr(payload, 'usuario_executor', None),
            'report_url': None,
            'analysis_report': None
        }
        return job_id

    def run_analysis(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return
        job['status'] = 'processing'
        job['analysis_report'] = f"Análise concluída para o job {job_id}"
        job['report_url'] = f"http://localhost/reports/{job_id}"
        job['status'] = 'completed'
        self.reports[job_id] = job

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job['report_url'],
            'analysis_report': job['analysis_report']
        }

    def get_report(self, job_id: str) -> Dict[str, Any]:
        job = self.reports.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job['report_url'],
            'analysis_report': job['analysis_report']
        }
