import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from mcp_server_fastapi import (
    app, _validate_and_normalize_gitlab_repo_name, _normalize_repo_name_by_type,
    _generate_analysis_name, _create_initial_job_data, _validate_job_for_approval,
    _validate_job_exists, _validate_analysis_exists, _get_report_from_job,
    _create_derived_job_data, _build_completed_response, StartAnalysisPayload,
    UpdateJobPayload, JobStatus, JobFields, JobActions
)

client = TestClient(app)

class TestValidateAndNormalizeGitlabRepoName:
    
    def test_validate_and_normalize_gitlab_repo_name_com_id_numerico(self):
        result = _validate_and_normalize_gitlab_repo_name("123456")
        assert result == "123456"
        
        result = _validate_and_normalize_gitlab_repo_name(" 789012 ")
        assert result == "789012"
    
    def test_validate_and_normalize_gitlab_repo_name_com_path_completo(self):
        result = _validate_and_normalize_gitlab_repo_name("meugrupo/meuprojeto")
        assert result == "meugrupo/meuprojeto"
        
        result = _validate_and_normalize_gitlab_repo_name("namespace/subgrupo/projeto")
        assert result == "namespace/subgrupo/projeto"
    
    def test_validate_and_normalize_gitlab_repo_name_invalido(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_and_normalize_gitlab_repo_name("invalid")
        assert exc_info.value.status_code == 400
        assert "Formato de repositório GitLab inválido" in str(exc_info.value.detail)
        
        with pytest.raises(HTTPException) as exc_info:
            _validate_and_normalize_gitlab_repo_name("apenas/")
        assert exc_info.value.status_code == 400
        assert "Path GitLab inválido" in str(exc_info.value.detail)
        
        with pytest.raises(HTTPException) as exc_info:
            _validate_and_normalize_gitlab_repo_name("")
        assert exc_info.value.status_code == 400

class TestStartAnalysisEndpoint:
    
    @patch('mcp_server_fastapi.container')
    def test_start_analysis_endpoint_caminho_feliz(self, mock_container):
        mock_job_store = Mock()
        mock_analysis_service = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        
        payload = {
            "repo_name": "test/repo",
            "projeto": "test-project",
            "analysis_type": "geracao_codigo_a_partir_de_reuniao",
            "repository_type": "github"
        }
        
        response = client.post("/start-analysis", json=payload)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "job_id" in response_data
        assert len(response_data["job_id"]) > 0
        
        mock_job_store.set_job.assert_called_once()
        mock_analysis_service.register_analysis.assert_called_once()
    
    def test_start_analysis_endpoint_input_invalido(self):
        payload = {
            "repo_name": "",
            "projeto": "test-project",
            "analysis_type": "invalid_type",
            "repository_type": "github"
        }
        
        response = client.post("/start-analysis", json=payload)
        assert response.status_code == 422

class TestUpdateJobStatusEndpoint:
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_approve(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job = {
            JobFields.STATUS: JobStatus.PENDING_APPROVAL,
            JobFields.DATA: {
                JobFields.PAUSED_AT_STEP: 2
            }
        }
        mock_job_store.get_job.return_value = mock_job
        
        payload = {
            "job_id": job_id,
            "action": "approve",
            "instrucoes_extras": "Instruções adicionais"
        }
        
        response = client.post("/update-job-status", json=payload)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == job_id
        assert response_data[JobFields.STATUS] == JobStatus.WORKFLOW_STARTED
        assert response_data["message"] == "Aprovação recebida."
        
        mock_job_store.set_job.assert_called()
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_reject(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job = {
            JobFields.STATUS: JobStatus.PENDING_APPROVAL,
            JobFields.DATA: {}
        }
        mock_job_store.get_job.return_value = mock_job
        
        payload = {
            "job_id": job_id,
            "action": "reject"
        }
        
        response = client.post("/update-job-status", json=payload)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == job_id
        assert response_data[JobFields.STATUS] == JobStatus.REJECTED
        assert response_data["message"] == "Processo encerrado."
    
    @patch('mcp_server_fastapi.container')
    def test_update_job_status_job_nao_encontrado(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job_store.get_job.return_value = None
        
        payload = {
            "job_id": job_id,
            "action": "approve"
        }
        
        response = client.post("/update-job-status", json=payload)
        assert response.status_code == 400
        assert "Job não encontrado ou não está aguardando aprovação" in response.json()["detail"]
        
        mock_job = {
            JobFields.STATUS: JobStatus.COMPLETED,
            JobFields.DATA: {}
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = client.post("/update-job-status", json=payload)
        assert response.status_code == 400

class TestGetJobReportEndpoint:
    
    @patch('mcp_server_fastapi.container')
    def test_get_job_report_job_inexistente(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job_store.get_job.return_value = None
        
        response = client.get(f"/jobs/{job_id}/report")
        assert response.status_code == 404
        assert "Job ID não encontrado ou expirado" in response.json()["detail"]
    
    @patch('mcp_server_fastapi.container')
    def test_get_job_report_sem_relatorio(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job = {
            JobFields.STATUS: JobStatus.COMPLETED,
            JobFields.DATA: {}
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = client.get(f"/jobs/{job_id}/report")
        assert response.status_code == 404
        assert "Relatório não encontrado para este job" in response.json()["detail"]

class TestGetStatusEndpoint:
    
    @patch('mcp_server_fastapi.container')
    def test_get_status_completed(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job = {
            JobFields.STATUS: JobStatus.COMPLETED,
            JobFields.DATA: {
                JobFields.GERAR_RELATORIO_APENAS: False,
                JobFields.COMMIT_DETAILS: [
                    {
                        JobFields.SUCCESS: True,
                        JobFields.PR_URL: "https://github.com/test/repo/pull/1",
                        JobFields.BRANCH_NAME: "feature-branch",
                        JobFields.ARQUIVOS_MODIFICADOS: ["file1.py", "file2.py"]
                    }
                ],
                JobFields.DIAGNOSTIC_LOGS: {"step1": "completed"},
                JobFields.REPORT_BLOB_URL: "https://blob.storage/report.html"
            }
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = client.get(f"/status/{job_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == job_id
        assert response_data["status"] == JobStatus.COMPLETED
        assert len(response_data["summary"]) == 1
        assert response_data["summary"][0]["pull_request_url"] == "https://github.com/test/repo/pull/1"
        assert response_data["report_blob_url"] == "https://blob.storage/report.html"
    
    @patch('mcp_server_fastapi.container')
    def test_get_status_failed(self, mock_container):
        mock_job_store = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        
        job_id = str(uuid.uuid4())
        mock_job = {
            JobFields.STATUS: JobStatus.FAILED,
            JobFields.ERROR_DETAILS: "Erro durante execução",
            JobFields.DATA: {
                JobFields.DIAGNOSTIC_LOGS: {"error": "detailed error info"},
                JobFields.REPORT_BLOB_URL: "https://blob.storage/error-report.html"
            }
        }
        mock_job_store.get_job.return_value = mock_job
        
        response = client.get(f"/status/{job_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["job_id"] == job_id
        assert response_data["status"] == JobStatus.FAILED
        assert response_data["error_details"] == "Erro durante execução"
        assert response_data["diagnostic_logs"]["error"] == "detailed error info"

class TestGetAnalysisByNameEndpoint:
    
    @patch('mcp_server_fastapi.container')
    def test_get_analysis_by_name_inexistente(self, mock_container):
        mock_job_store = Mock()
        mock_analysis_service = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        
        analysis_name = "nonexistent-analysis"
        mock_analysis_service.find_job_by_analysis_name.return_value = None
        
        response = client.get(f"/analyses/by-name/{analysis_name}")
        assert response.status_code == 404
        assert f"Análise com nome '{analysis_name}' não encontrada" in response.json()["detail"]

class TestStartCodeGenerationFromReportEndpoint:
    
    @patch('mcp_server_fastapi.container')
    def test_start_code_generation_from_report_caminho_feliz(self, mock_container):
        mock_job_store = Mock()
        mock_analysis_service = Mock()
        mock_container.get_job_store.return_value = mock_job_store
        mock_container.get_analysis_name_service.return_value = mock_analysis_service
        
        analysis_name = "test-analysis"
        original_job_id = str(uuid.uuid4())
        mock_analysis_service.find_job_by_analysis_name.return_value = original_job_id
        
        original_job = {
            JobFields.STATUS: JobStatus.COMPLETED,
            JobFields.DATA: {
                JobFields.REPO_NAME: "test/repo",
                JobFields.PROJETO: "test-project",
                JobFields.BRANCH_NAME: "main",
                JobFields.MODEL_NAME: "gpt-4",
                JobFields.USAR_RAG: False,
                JobFields.ARQUIVOS_ESPECIFICOS: None,
                JobFields.REPOSITORY_TYPE: "github",
                JobFields.ANALYSIS_REPORT: "Relatório de análise completo"
            }
        }
        mock_job_store.get_job.return_value = original_job
        
        response = client.post(f"/start-code-generation-from-report/{analysis_name}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "job_id" in response_data
        assert len(response_data["job_id"]) > 0
        
        mock_job_store.set_job.assert_called()
        mock_analysis_service.register_analysis.assert_called_with(
            f"{analysis_name}-implementation", 
            response_data["job_id"]
        )

class TestUtilityFunctions:
    
    def test_normalize_repo_name_by_type_gitlab(self):
        result = _normalize_repo_name_by_type("123456", "gitlab")
        assert result == "123456"
        
        result = _normalize_repo_name_by_type("group/project", "gitlab")
        assert result == "group/project"
    
    def test_normalize_repo_name_by_type_github(self):
        result = _normalize_repo_name_by_type("user/repo", "github")
        assert result == "user/repo"
    
    def test_generate_analysis_name_provided(self):
        job_id = str(uuid.uuid4())
        result = _generate_analysis_name("custom-name", job_id)
        assert result == "custom-name"
    
    def test_generate_analysis_name_auto_generated(self):
        job_id = str(uuid.uuid4())
        result = _generate_analysis_name(None, job_id)
        assert result.startswith("analysis-")
        assert len(result.split("-")[1]) == 8
    
    def test_validate_job_for_approval_valid(self):
        job = {JobFields.STATUS: JobStatus.PENDING_APPROVAL}
        _validate_job_for_approval(job, "test-job-id")
    
    def test_validate_job_for_approval_invalid(self):
        job = {JobFields.STATUS: JobStatus.COMPLETED}
        with pytest.raises(HTTPException) as exc_info:
            _validate_job_for_approval(job, "test-job-id")
        assert exc_info.value.status_code == 400
        
        with pytest.raises(HTTPException) as exc_info:
            _validate_job_for_approval(None, "test-job-id")
        assert exc_info.value.status_code == 400
    
    def test_validate_job_exists_valid(self):
        job = {JobFields.STATUS: JobStatus.COMPLETED}
        _validate_job_exists(job, "test-job-id")
    
    def test_validate_job_exists_invalid(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_job_exists(None, "test-job-id")
        assert exc_info.value.status_code == 404
    
    def test_validate_analysis_exists_valid(self):
        mock_analysis_service = Mock()
        mock_analysis_service.find_job_by_analysis_name.return_value = "job-id"
        
        result = _validate_analysis_exists("test-analysis", mock_analysis_service)
        assert result == "job-id"
    
    def test_validate_analysis_exists_invalid(self):
        mock_analysis_service = Mock()
        mock_analysis_service.find_job_by_analysis_name.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            _validate_analysis_exists("test-analysis", mock_analysis_service)
        assert exc_info.value.status_code == 404
    
    def test_get_report_from_job_valid(self):
        job = {
            JobFields.DATA: {
                JobFields.ANALYSIS_REPORT: "Test report"
            }
        }
        result = _get_report_from_job(job, "job-id")
        assert result == "Test report"
    
    def test_get_report_from_job_invalid(self):
        job = {JobFields.DATA: {}}
        with pytest.raises(HTTPException) as exc_info:
            _get_report_from_job(job, "job-id")
        assert exc_info.value.status_code == 404
    
    def test_create_initial_job_data(self):
        payload = StartAnalysisPayload(
            repo_name="test/repo",
            projeto="test-project",
            analysis_type="geracao_codigo_a_partir_de_reuniao",
            repository_type="github"
        )
        
        result = _create_initial_job_data(payload, "normalized-repo", "analysis-name")
        
        assert result[JobFields.STATUS] == JobStatus.STARTING
        assert result[JobFields.DATA][JobFields.REPO_NAME] == "normalized-repo"
        assert result[JobFields.DATA][JobFields.ORIGINAL_REPO_NAME] == "test/repo"
        assert result[JobFields.DATA][JobFields.PROJETO] == "test-project"
        assert result[JobFields.DATA][JobFields.ANALYSIS_NAME] == "analysis-name"
    
    def test_create_derived_job_data(self):
        original_job = {
            JobFields.DATA: {
                JobFields.REPO_NAME: "test/repo",
                JobFields.PROJETO: "test-project",
                JobFields.BRANCH_NAME: "main",
                JobFields.MODEL_NAME: "gpt-4",
                JobFields.USAR_RAG: False,
                JobFields.ARQUIVOS_ESPECIFICOS: None,
                JobFields.REPOSITORY_TYPE: "github"
            }
        }
        
        result = _create_derived_job_data(original_job, "test-analysis", "normalized-repo", "Test report")
        
        assert result[JobFields.STATUS] == JobStatus.STARTING
        assert result[JobFields.DATA][JobFields.REPO_NAME] == "normalized-repo"
        assert result[JobFields.DATA][JobFields.ORIGINAL_ANALYSIS_TYPE] == "implementacao"
        assert "Gerar código baseado no seguinte relatório" in result[JobFields.DATA][JobFields.INSTRUCOES_EXTRAS]
        assert result[JobFields.DATA][JobFields.ANALYSIS_NAME] == "test-analysis-implementation"
    
    def test_build_completed_response_relatorio_apenas(self):
        job_id = "test-job-id"
        job = {
            JobFields.DATA: {
                JobFields.GERAR_RELATORIO_APENAS: True,
                JobFields.ANALYSIS_REPORT: "Test report"
            }
        }
        blob_url = "https://blob.storage/report.html"
        
        result = _build_completed_response(job_id, job, blob_url)
        
        assert result.job_id == job_id
        assert result.status == JobStatus.COMPLETED
        assert result.analysis_report == "Test report"
        assert result.report_blob_url == blob_url
        assert result.summary is None
    
    def test_build_completed_response_com_prs(self):
        job_id = "test-job-id"
        job = {
            JobFields.DATA: {
                JobFields.GERAR_RELATORIO_APENAS: False,
                JobFields.COMMIT_DETAILS: [
                    {
                        JobFields.SUCCESS: True,
                        JobFields.PR_URL: "https://github.com/test/repo/pull/1",
                        JobFields.BRANCH_NAME: "feature-branch",
                        JobFields.ARQUIVOS_MODIFICADOS: ["file1.py", "file2.py"]
                    }
                ],
                JobFields.DIAGNOSTIC_LOGS: {"step1": "completed"}
            }
        }
        blob_url = "https://blob.storage/report.html"
        
        result = _build_completed_response(job_id, job, blob_url)
        
        assert result.job_id == job_id
        assert result.status == JobStatus.COMPLETED
        assert len(result.summary) == 1
        assert result.summary[0].pull_request_url == "https://github.com/test/repo/pull/1"
        assert result.summary[0].branch_name == "feature-branch"
        assert result.summary[0].arquivos_modificados == ["file1.py", "file2.py"]
        assert result.diagnostic_logs == {"step1": "completed"}
        assert result.report_blob_url == blob_url
