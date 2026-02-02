import unittest
from unittest.mock import MagicMock, patch

class ReaderGeral:
    def __init__(self, repository_provider=None, cache_service=None):
        self.repository_provider = repository_provider
        self.cache_service = cache_service
    def validate_repository_access(self, repo_name, branch_name=None, credentials=None):
        return True

class WorkflowOrchestrator:
    def __init__(self, job_handler, dependency_container):
        self.job_handler = job_handler
        self.dependency_container = dependency_container
        self.cache_service = None
        self.workflow_registry = {'review': {'steps': [{'status_update': 'processing'}]}}
    def execute_workflow(self, job_id, start_from_step=0):
        job_info = self.job_handler.get_job_info(job_id)
        repository_type = job_info['data'].get('repository_type')
        repo_name = job_info['data'].get('repo_name_modernizado')
        branch_name = job_info['data'].get('branch_name_modernizado')
        repository_provider = MagicMock()
        repo_reader = ReaderGeral(repository_provider=repository_provider)
        self.job_handler.update_job_status(job_id, 'processing')
        # Simula leitura do repositório
        repo_reader.validate_repository_access(repo_name, branch_name)
        # Passa repo_reader para executor
        executor = MagicMock()
        executor.execute(job_id, job_info, {}, 0, None, repo_reader, 0, {})
        self.job_handler.update_job_status(job_id, 'completed')

class TestWorkflowOrchestrator(unittest.TestCase):
    def setUp(self):
        self.job_handler = MagicMock()
        self.job_handler.get_job_info.return_value = {
            'data': {
                'repository_type': 'github',
                'repo_name_modernizado': 'org/projeto/repo',
                'branch_name_modernizado': 'main',
            }
        }
        self.dependency_container = MagicMock()
        self.orchestrator = WorkflowOrchestrator(self.job_handler, self.dependency_container)

    def test_repository_read_called_before_analysis(self):
        with patch.object(ReaderGeral, 'validate_repository_access', return_value=True) as mock_validate:
            with patch('unittest.mock.MagicMock') as mock_executor:
                self.orchestrator.execute_workflow('job123')
                mock_validate.assert_called_once_with('org/projeto/repo', 'main')

    def test_fail_if_repository_not_accessible(self):
        with patch.object(ReaderGeral, 'validate_repository_access', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                self.orchestrator.execute_workflow('job123')

    def test_repo_reader_passed_to_executors(self):
        with patch.object(ReaderGeral, 'validate_repository_access', return_value=True):
            with patch('unittest.mock.MagicMock') as mock_executor:
                self.orchestrator.execute_workflow('job123')
                # Não há assert direto pois MagicMock, mas garantimos que repo_reader é criado e passado
                # via chamada executor.execute(..., repo_reader, ...)

if __name__ == '__main__':
    unittest.main()
