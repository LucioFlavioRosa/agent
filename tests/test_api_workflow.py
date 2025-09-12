import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from mcp_server_fastapi import app

class TestAPIWorkflow:
    
    @pytest.fixture
    def client(self):
        """Cria um cliente de teste para a API."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_workflow_orchestrator(self):
        """Mock do WorkflowOrchestrator."""
        with patch('mcp_server_fastapi.workflow_orchestrator') as mock:
            yield mock
    
    @pytest.fixture
    def mock_job_store(self):
        """Mock do JobStore."""
        with patch('mcp_server_fastapi.job_store') as mock:
            yield mock
    
    @pytest.fixture
    def mock_blob_storage(self):
        """Mock do BlobStorageService."""
        with patch('mcp_server_fastapi.blob_storage') as mock:
            yield mock
    
    def test_start_analysis_with_gerar_novo_relatorio_true(self, client, mock_workflow_orchestrator, mock_job_store):
        """Testa o endpoint start-analysis com gerar_novo_relatorio=True."""
        payload = {
            "repo_name": "test/repo",
            "projeto": "test-project",
            "analysis_type": "refatoracao",  # Assumindo que existe no WORKFLOW_REGISTRY
            "branch_name": "main",
            "gerar_novo_relatorio": True,
            "gerar_relatorio_apenas": True,
            "analysis_name": "test-analysis",
            "repository_type": "github"
        }
        
        # Mock do job store
        mock_job_store.set_job.return_value = None
        
        response = client.post("/start-analysis", json=payload)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "job_id" in response_data
        
        # Verifica se o job foi criado com os parâmetros corretos
        mock_job_store.set_job.assert_called_once()
        job_id, job_data = mock_job_store.set_job.call_args[0]
        assert job_data['data']['gerar_novo_relatorio'] is True
        assert job_data['data']['analysis_name'] == "test-analysis"
    
    def test_start_analysis_with_gerar_novo_relatorio_false(self, client, mock_workflow_orchestrator, mock_job_store):
        """Testa o endpoint start-analysis com gerar_novo_relatorio=False."""
        payload = {
            "repo_name": "test/repo",
            "projeto": "test-project",
            "analysis_type": "refatoracao",  # Assumindo que existe no WORKFLOW_REGISTRY
            "branch_name": "main",
            "gerar_novo_relatorio": False,
            "gerar_relatorio_apenas": True,
            "analysis_name": "existing-analysis",
            "repository_type": "github"
        }
        
        # Mock do job store
        mock_job_store.set_job.return_value = None
        
        response = client.post("/start-analysis", json=payload)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "job_id" in response_data
        
        # Verifica se o job foi criado com os parâmetros corretos
        mock_job_store.set_job.assert_called_once()
        job_id, job_data = mock_job_store.set_job.call_args[0]
        assert job_data['data']['gerar_novo_relatorio'] is False
        assert job_data['data']['analysis_name'] == "existing-analysis"
    
    @patch('mcp_server_fastapi.run_workflow_task')
    def test_workflow_execution_with_existing_report(self, mock_run_workflow, client, mock_workflow_orchestrator, mock_job_store, mock_blob_storage):
        """Testa que o workflow é executado corretamente quando há relatório existente."""
        # Simula um job com gerar_novo_relatorio=False
        job_data = {
            'status': 'starting',
            'data': {
                'repo_name': 'test/repo',
                'projeto': 'test-project',
                'original_analysis_type': 'refatoracao',
                'gerar_novo_relatorio': False,
                'gerar_relatorio_apenas': True,
                'analysis_name': 'existing-analysis',
                'repository_type': 'github',
                'branch_name': 'main'
            }
        }
        
        mock_job_store.get_job.return_value = job_data
        mock_blob_storage.read_report.return_value = "Relatório existente"
        
        payload = {
            "repo_name": "test/repo",
            "projeto": "test-project",
            "analysis_type": "refatoracao",
            "branch_name": "main",
            "gerar_novo_relatorio": False,
            "gerar_relatorio_apenas": True,
            "analysis_name": "existing-analysis",
            "repository_type": "github"
        }
        
        response = client.post("/start-analysis", json=payload)
        
        assert response.status_code == 200
        
        # Verifica se o workflow foi iniciado
        mock_run_workflow.assert_called_once()
    
    def test_get_status_with_completed_report_only_job(self, client, mock_job_store):
        """Testa o endpoint de status para um job completado em modo apenas relatório."""
        job_id = "test-job-123"
        job_data = {
            'status': 'completed',
            'data': {
                'gerar_relatorio_apenas': True,
                'analysis_report': 'Relatório de teste',
                'report_blob_url': 'https://blob.storage/report.txt'
            }
        }
        
        mock_job_store.get_job.return_value = job_data
        
        response = client.get(f"/status/{job_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data['status'] == 'completed'
        assert response_data['analysis_report'] == 'Relatório de teste'
        assert response_data['report_blob_url'] == 'https://blob.storage/report.txt'
        assert response_data['summary'] is None  # Para modo apenas relatório
    
    def test_get_analysis_by_name_with_existing_report(self, client, mock_job_store):
        """Testa o endpoint de busca por nome de análise."""
        analysis_name = "test-analysis"
        job_id = "test-job-123"
        
        # Simula o mapeamento analysis_name -> job_id
        with patch('mcp_server_fastapi.analysis_name_to_job_id', {analysis_name: job_id}):
            job_data = {
                'status': 'completed',
                'data': {
                    'analysis_report': 'Relatório encontrado',
                    'report_blob_url': 'https://blob.storage/report.txt'
                }
            }
            
            mock_job_store.get_job.return_value = job_data
            
            response = client.get(f"/analyses/by-name/{analysis_name}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data['job_id'] == job_id
            assert response_data['analysis_name'] == analysis_name
            assert response_data['analysis_report'] == 'Relatório encontrado'
            assert response_data['report_blob_url'] == 'https://blob.storage/report.txt'