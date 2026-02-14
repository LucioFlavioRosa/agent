import pytest
from httpx import AsyncClient
from fastapi import status
from backend.app.main import app
import motor.motor_asyncio
import asyncio

@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="module")
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="function")
async def setup_groups_and_company():
    mongo_service = app.state.mongo_service
    db = mongo_service.db
    await db.groups.delete_many({})
    await db.companies.delete_many({})
    company_id = "company-id-999"
    group_id = "group-devs-id"
    # Cria company
    company = {
        "_id": company_id,
        "name": "Empresa Teste",
        "domain": "test.com"
    }
    await db.companies.insert_one(company)
    # Cria grupo
    group = {
        "_id": group_id,
        "name": "Desenvolvedores Backend",
        "company_id": company_id,
        "allowed_agents": ["agent_code_generation", "agent_refactoring", "agent_unit_tests"],
        "settings": {"max_daily_tokens": 50000, "can_create_projects": True}
    }
    await db.groups.insert_one(group)
    yield {
        "company_id": company_id,
        "group_id": group_id
    }
    await db.groups.delete_many({})
    await db.companies.delete_many({})

@pytest.mark.anyio
async def test_get_group_by_id_success(test_client, setup_groups_and_company):
    group_id = setup_groups_and_company["group_id"]
    response = await test_client.get(f"/groups/{group_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Desenvolvedores Backend"
    assert data["company_id"] == setup_groups_and_company["company_id"]
    assert "allowed_agents" in data
    assert "settings" in data

@pytest.mark.anyio
async def test_get_group_by_id_not_found(test_client):
    response = await test_client.get("/groups/group-nonexistent-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.text or "not found" in response.text.lower()

@pytest.mark.anyio
async def test_list_groups_by_company_success(test_client, setup_groups_and_company):
    company_id = setup_groups_and_company["company_id"]
    response = await test_client.get(f"/groups?company_id={company_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["company_id"] == company_id

@pytest.mark.anyio
async def test_list_groups_by_company_empty(test_client):
    response = await test_client.get("/groups?company_id=company-no-groups")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

@pytest.mark.anyio
async def test_list_groups_by_company_invalid_company_id(test_client):
    response = await test_client.get("/groups?company_id=")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "company_id" in response.text or "obrigatório" in response.text.lower()
