import pytest
from services.workflow_orchestrator import WorkflowOrchestrator
from services.dependency_container import DependencyContainer

class DummyJobManager:
    def get_job_info(self, job_id):
        return {
            'data': {
                'repo_name_modernizado': 'TestRepo',
                'original_analysis_type': 'criacao_epicos_azure_devops',
                'analysis_name': 'dummy-analysis',
                'projeto': 'TestProject',
                'repository_type': 'azure',
                'repo_name': 'TestRepo',
                'branch_name_modernizado': 'main',
                'executar_steps_incrementalmente': True,
                'max_steps_per_batch': 2,
                'gerar_relatorio_apenas': False
            },
            'status': 'starting'
        }
    def update_job_status(self, job_id, status):
        pass
    def update_job(self, job_id, job_info):
        pass
    def get_step_result(self, job_info, step_index):
        return {}
    def set_paused_step(self, job_info, step_index):
        job_info['data']['paused_at_step'] = step_index

class DummyBlobStorage:
    def read_report(self, **kwargs):
        return None
    def save_report_to_blob(self, job_id, job_info, report_text):
        return f"https://dummy.blob/{job_id}/report.md"
    def get_report_url(self, **kwargs):
        return f"https://dummy.blob/report.md"
    def update_job_tracker(self, report_blob_url, job_id):
        pass

@pytest.fixture
def orchestrator():
    workflow_registry = {
        'criacao_epicos_azure_devops': {
            'steps': [
                {'status_update': 'pending_approval', 'requires_approval': True},
                {'status_update': 'workflow_started', 'requires_approval': False}
            ]
        }
    }
    return WorkflowOrchestrator(
        job_manager=DummyJobManager(),
        blob_storage=DummyBlobStorage(),
        workflow_registry=workflow_registry
    )

def test_execute_workflow_epicos(orchestrator):
    job_id = "dummy-job-id"
    orchestrator.execute_workflow(job_id, start_from_step=0)
    # Não há commits ou builds neste MCP, apenas fluxo de steps e relatórios

def test_handle_approval_step(orchestrator):
    job_id = "dummy-job-id"
    job_info = orchestrator.job_handler.get_job_info(job_id)
    step_index = 0
    step_result = {'relatorio': 'Relatório de aprovação'}
    orchestrator.handle_approval_step(job_id, job_info, step_index, step_result)
    assert job_info['status'] == 'pending_approval'
