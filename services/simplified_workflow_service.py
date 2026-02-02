from typing import Any, Dict

VALID_AGENT_TYPES = ['processador']

class SimplifiedWorkflowService:
    def __init__(self):
        self.jobs = {}
        self.reports = {}

    def start_analysis(self, payload: Any) -> str:
        agent_type = getattr(payload, 'agent_type', None)
        if agent_type not in VALID_AGENT_TYPES:
            raise ValueError(f"Tipo de agente inválido: {agent_type}. Apenas 'processador' é permitido.")
        job_id = f"job_{len(self.jobs)+1}"
        self.jobs[job_id] = {
            'status': 'started',
            'payload': payload,
            'report_url': None,
            'analysis_report': None
        }
        return job_id

    def run_analysis(self, job_id: str):
        # Simulação de análise mínima
        job = self.jobs.get(job_id)
        if not job:
            return
        job['status'] = 'processing'
        # Aqui rodaria o agente processador
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
