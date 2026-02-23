import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

import sys
sys.path.append('backend/app')

from main import app

class FakeSecretsManager:
    async def get_secret(self, base_name, company_id, group_id=None):
        if group_id:
            return f"fake_{base_name}_{company_id}_{group_id}"
        return f"fake_{base_name}_{company_id}"

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
@patch("main.SecretsManager", new=FakeSecretsManager)
async def test_start_analysis_with_group(client):
    data = {
        "project_id": "proj1",
        "job_id": "job1",
        "company_id": "123",
        "group_ids": "456"
    }
    response = client.post("/start", data=data)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"

@pytest.mark.asyncio
@patch("main.SecretsManager", new=FakeSecretsManager)
async def test_start_analysis_without_group(client):
    data = {
        "project_id": "proj2",
        "job_id": "job2",
        "company_id": "789"
    }
    response = client.post("/start", data=data)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
