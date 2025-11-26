import pytest
from fastapi.testclient import TestClient
from mcp_azure_board.mcp_server_fastapi import app
from mcp_azure_board.services.workflow_orchestrator import WorkflowOrchestrator
from mcp_azure_board.services.dependency_container import DependencyContainer
from mcp_azure_board.models import JobStatus

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def orchestrator():
    container = DependencyContainer()
    workflow_registry_service = container.get_workflow_registry_service()
    workflow_registry = workflow_registry_service.get_workflow_registry()
    job_manager = container.get_job_manager()
    blob_storage = container.get_blob_storage()
    return WorkflowOrchestrator(
        job_manager=job_manager,
        blob_storage=blob_storage,
        workflow_registry=workflow_registry,
        dependency_container=container
    )

def test_execute_workflow_criacao_epicos(orchestrator):
    job_id = "test-job-epico"
    job_info = {
        "data": {
            "original_analysis_type": "criacao_epicos_azure_devops",
            "repo_name_modernizado": "org/proj/repo",
            "organization": "org",
            "project": "proj",
            "analysis_name": "test-analysis-epico",
            "repository_type": "azure"
        }
    }
    orchestrator.job_handler.job_manager.set_job(job_id, job_info)
    try:
        orchestrator.execute_workflow(job_id)
    except Exception as e:
        pytest.fail(f"Falha ao executar workflow de criação de épicos: {e}")

def test_execute_workflow_criacao_features(orchestrator):
    job_id = "test-job-feature"
    job_info = {
        "data": {
            "original_analysis_type": "criacao_features_azure_devops",
            "repo_name_modernizado": "org/proj/repo",
            "organization": "org",
            "project": "proj",
            "epic_id": "12345",
            "analysis_name": "test-analysis-feature",
            "repository_type": "azure"
        }
    }
    orchestrator.job_handler.job_manager.set_job(job_id, job_info)
    try:
        orchestrator.execute_workflow(job_id, start_from_step=1)
    except Exception as e:
        pytest.fail(f"Falha ao executar workflow de criação de features: {e}")

def test_execute_workflow_criacao_tarefas(orchestrator):
    job_id = "test-job-tarefa"
    job_info = {
        "data": {
            "original_analysis_type": "criacao_tarefas_azure_devops",
            "repo_name_modernizado": "org/proj/repo",
            "organization": "org",
            "project": "proj",
            "feature_id": "54321",
            "analysis_name": "test-analysis-tarefa",
            "repository_type": "azure"
        }
    }
    orchestrator.job_handler.job_manager.set_job(job_id, job_info)
    try:
        orchestrator.execute_workflow(job_id, start_from_step=1)
    except Exception as e:
        pytest.fail(f"Falha ao executar workflow de criação de tarefas: {e}")

def test_execute_workflow_revisor_tarefas(orchestrator):
    job_id = "test-job-revisor"
    job_info = {
        "data": {
            "original_analysis_type": "revisor_tarefas",
            "repo_name_modernizado": "org/proj/repo",
            "organization": "org",
            "project": "proj",
            "task_id": "67890",
            "analysis_name": "test-analysis-revisor",
            "repository_type": "azure"
        }
    }
    orchestrator.job_handler.job_manager.set_job(job_id, job_info)
    try:
        orchestrator.execute_workflow(job_id)
    except Exception as e:
        pytest.fail(f"Falha ao executar workflow de revisão de tarefas: {e}")
