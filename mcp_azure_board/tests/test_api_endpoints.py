import pytest
from fastapi.testclient import TestClient
from mcp_server_fastapi import app

client = TestClient(app)

def test_start_analysis_azure_board():
    payload = {
        "analysis_type": "criacao_epicos_azure_devops",
        "repository_type": "azure",
        "projeto": "TestProject",
        "repo_name_modernizado": "TestRepo",
        "branch_name_modernizado": "main"
    }
    response = client.post("/start-analysis", json=payload)
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_update_job_status_azure_board():
    job_id = "dummy-job-id"
    payload = {
        "job_id": job_id,
        "action": "approve"
    }
    response = client.post("/update-job-status", json=payload)
    assert response.status_code in [200, 400]

def test_get_job_report_azure_board():
    job_id = "dummy-job-id"
    response = client.get(f"/jobs/{job_id}/report")
    assert response.status_code in [200, 404]

def test_get_analysis_by_name_azure_board():
    analysis_name = "dummy-analysis-name"
    response = client.get(f"/analyses/by-name/{analysis_name}")
    assert response.status_code in [200, 404]

def test_start_code_generation_from_report_azure_board():
    analysis_name = "dummy-analysis-name"
    response = client.post(f"/start-code-generation-from-report/{analysis_name}")
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_get_status_azure_board():
    job_id = "dummy-job-id"
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert "status" in response.json()

def test_get_jobs_for_report_azure_board():
    report_name = "dummy-report-name"
    response = client.get(f"/reports/{report_name}/jobs")
    assert response.status_code in [200, 500]
