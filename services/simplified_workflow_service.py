import uuid
from typing import Dict, Any

class SimplifiedWorkflowService:
    def __init__(self):
        self.jobs = {}

    def start_analysis(self, payload):
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            'status': 'PROCESSING',
            'payload': payload.dict(),
            'analysis_report': None,
            'report_url': None
        }
        return job_id

    def run_analysis(self, job_id):
        job = self.jobs.get(job_id)
        if not job:
            return
        # Simulação: leitura do código do repositório e execução do agente
        # Aqui você integraria com agentes reais e leitura do repo
        job['analysis_report'] = f"Relatório gerado pelo agente {job['payload']['agent_type']} para o repositório {job['payload']['repo_name']} na branch {job['payload']['branch_name']}."
        job['report_url'] = f"https://fake-storage.example.com/reports/{job_id}.txt"
        job['status'] = 'COMPLETED'

    def get_status(self, job_id):
        job = self.jobs.get(job_id)
        if not job:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job['report_url'],
            'analysis_report': job['analysis_report']
        }

    def get_report(self, job_id):
        job = self.jobs.get(job_id)
        if not job or not job['analysis_report']:
            return None
        return {
            'job_id': job_id,
            'status': job['status'],
            'report_url': job['report_url'],
            'analysis_report': job['analysis_report']
        }
