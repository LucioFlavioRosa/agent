import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from mcp_server_fastapi import app, _validate_and_normalize_gitlab_repo_name, _normalize_repo_name_by_type


class TestMCPServerFastAPI:
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_validate_and_normalize_gitlab_repo_name_with_project_id(self):
        result = _validate_and_normalize_gitlab_repo_name("12345")
        assert result == "12345"
        
        result = _validate_and_normalize_gitlab_repo_name(" 67890 ")
        assert result == "67890"
    
    def test_validate_and_normalize_gitlab_repo_name_with_path(self):
        result = _validate_and_normalize_gitlab_repo_name("mygroup/myproject")
        assert result == "mygroup/myproject"
        
        result = _validate_and_normalize_gitlab_repo_name("org/subgroup/project")
        assert result == "org/subgroup/project"
    
    def test_validate_and_normalize_gitlab_repo_name_invalid_format(self):
        with pytest.raises(Exception) as exc_info:
            _validate_and_normalize_gitlab_repo_name("invalid")
        assert "Path GitLab inválido" in str(exc_info.value)
        
        with pytest.raises(Exception) as exc_info:
            _validate_and_normalize_gitlab_repo_name("")
        assert "Formato de repositório GitLab inválido" in str(exc_info.value)
    
    def test_normalize_repo_name_by_type_gitlab(self):
        result = _normalize_repo_name_by_type("mygroup/project", "gitlab")
        assert result == "mygroup/project"
        
        result = _normalize_repo_name_by_type("12345", "gitlab")
        assert result == "12345"
    
    def test_normalize_repo_name_by_type_non_gitlab(self):
        result = _normalize_repo_name_by_type("owner/repo", "github")
        assert result == "owner/repo"
        
        result = _normalize_repo_name_by_type("org/project/repo", "azure")
        assert result == "org/project/repo"
    
    @patch('mcp_server_fastapi.container')
    def test_start_analysis_success(self, mock_container):
        mock_job_store = Mock()
        mock_analysis_service = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        
        payload = {
            "repo_name": "test/repo",
            "projeto": "test-project",
            "analysis_type": "auditoria_testes",
            "repository_type": "github"
        }
        
        with patch('mcp_server_fastapi.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('12345678-1234-5678-9012-123456789012')
            
            response = self.client.post("/start-analysis", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_id"] == "12345678-1234-5678-9012-123456789012"
    
    @patch('mcp_server_fastapi.container')
    def test_start_analysis_invalid_repository_type(self, mock_container):
        payload = {
            "repo_name": "test/repo",
            "projeto": "test-project",
            "analysis_type": "auditoria_testes",
            "repository_type": "invalid_type"
        }
        
        response = self.client.post("/start-analysis", json=payload)
        assert response.status_code == 422
    
    @patch('mcp_server_fastapi.container')
    def test_start_analysis_missing_required_fields(self, mock_container):
        payload = {
            "repo_name": "test/repo",
            "analysis_type": "auditoria_testes"
        }
        
        response = self.client.post("/start-analysis", json=payload)
        assert response.status_code == 422
    
    @patch('mcp_server_fastapi.container')
    def test_start_analysis_with_gitlab_project_id(self, mock_container):
        mock_job_store = Mock()
        mock_analysis_service = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        
        payload = {
            "repo_name": "12345",
            "projeto": "gitlab-project",
            "analysis_type": "auditoria_testes",
            "repository_type": "gitlab"
        }
        
        response = self.client.post("/start-analysis", json=payload)
        assert response.status_code == 200
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_approve(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        mock_job = {
            "status": "pending_approval",
            "data": {"paused_at_step": 1}
        }
        mock_job_store.get_job.return_value = mock_job
        
        payload = {
            "job_id": "test-job-123",
            "action": "approve",
            "instrucoes_extras": "Additional instructions"
        }
        
        response = self.client.post("/update-job-status", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "workflow_started"
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_reject(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        mock_job = {
            "status": "pending_approval",
            "data": {"paused_at_step": 1}
        }
        mock_job_store.get_job.return_value = mock_job
        
        payload = {
            "job_id": "test-job-456",
            "action": "reject"
        }
        
        response = self.client.post("/update-job-status", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "rejected"
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_job_not_found(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_job_store.get_job.return_value = None
        
        payload = {
            "job_id": "nonexistent-job",
            "action": "approve"
        }
        
        response = self.client.post("/update-job-status", json=payload)
        assert response.status_code == 400
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_invalid_status(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        mock_job = {
            "status": "completed",
            "data": {}
        }
        mock_job_store.get_job.return_value = mock_job
        
        payload = {
            "job_id": "completed-job",
            "action": "approve"
        }
        
        response = self.client.post("/update-job-status", json=payload)
        assert response.status_code == 400
    
    @patch('mcp_server_fastapi.container')
    def test_get_status_job_not_found(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_job_store.get_job.return_value = None
        
        response = self.client.get("/status/nonexistent-job")
        assert response.status_code == 404
    
    @patch('mcp_server_fastapi.container')
    def test_get_status_completed_job(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        mock_job = {
            "status": "completed",
            "data": {
                "gerar_relatorio_apenas": True,
                "analysis_report": "Test report content",
                "report_blob_url": "https://blob.storage/report.md"
            }
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = self.client.get("/status/completed-job")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "completed"
        assert data["analysis_report"] == "Test report content"
        assert data["report_blob_url"] == "https://blob.storage/report.md"
    
    @patch('mcp_server_fastapi.container')
    def test_get_status_failed_job(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        mock_job = {
            "status": "failed",
            "error_details": "Processing failed due to invalid input",
            "data": {
                "diagnostic_logs": {"error": "detailed error info"}
            }
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = self.client.get("/status/failed-job")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_details"] == "Processing failed due to invalid input"
        assert data["diagnostic_logs"]["error"] == "detailed error info"
    
    @patch('mcp_server_fastapi.container')
    def test_get_job_report_success(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        mock_job = {
            "data": {
                "analysis_report": "Detailed analysis report",
                "report_blob_url": "https://blob.storage/detailed-report.md"
            }
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = self.client.get("/jobs/report-job/report")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == "report-job"
        assert data["analysis_report"] == "Detailed analysis report"
        assert data["report_blob_url"] == "https://blob.storage/detailed-report.md"
    
    @patch('mcp_server_fastapi.container')
    def test_get_job_report_not_found(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_job_store.get_job.return_value = None
        
        response = self.client.get("/jobs/missing-job/report")
        assert response.status_code == 404
    
    @patch('mcp_server_fastapi.container')
    def test_get_analysis_by_name_success(self, mock_container):
        mock_job_store = Mock()
        mock_analysis_service = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        
        mock_analysis_service.find_job_by_analysis_name.return_value = "found-job-id"
        mock_job_store.get_job.return_value = {
            "data": {
                "analysis_report": "Analysis by name report",
                "report_blob_url": "https://blob.storage/named-analysis.md"
            }
        }
        
        response = self.client.get("/analyses/by-name/test-analysis")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == "found-job-id"
        assert data["analysis_name"] == "test-analysis"
        assert data["analysis_report"] == "Analysis by name report"
    
    @patch('mcp_server_fastapi.container')
    def test_get_analysis_by_name_not_found(self, mock_container):
        mock_analysis_service = Mock()
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        mock_analysis_service.find_job_by_analysis_name.return_value = None
        
        response = self.client.get("/analyses/by-name/missing-analysis")
        assert response.status_code == 404
    
    def test_start_analysis_with_unicode_data(self):
        with patch('mcp_server_fastapi.container') as mock_container:
            mock_job_store = Mock()
            mock_analysis_service = Mock()
            mock_container.get_job_store.return_value = mock_job_store
            mock_container.get_analysis_name_service.return_value = mock_analysis_service
            
            payload = {
                "repo_name": "测试组织/测试项目",
                "projeto": "Unicode项目 🚀",
                "analysis_type": "auditoria_testes",
                "repository_type": "github",
                "instrucoes_extras": "测试指令 with emoji 🎯"
            }
            
            response = self.client.post("/start-analysis", json=payload)
            assert response.status_code == 200
    
    def test_start_analysis_with_edge_case_values(self):
        with patch('mcp_server_fastapi.container') as mock_container:
            mock_job_store = Mock()
            mock_analysis_service = Mock()
            mock_container.get_job_store.return_value = mock_job_store
            mock_container.get_analysis_name_service.return_value = mock_analysis_service
            
            payload = {
                "repo_name": "a" * 100,  # Very long repo name
                "projeto": "edge-case-project",
                "analysis_type": "auditoria_testes",
                "repository_type": "github",
                "max_token_out": 50000,  # Maximum token limit
                "arquivos_especificos": ["file1.py"] * 1000  # Many files
            }
            
            response = self.client.post("/start-analysis", json=payload)
            assert response.status_code == 200