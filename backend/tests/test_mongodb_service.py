import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.services.mongodb_service import MongoDBService
from backend.app.models.permission_models import GroupPermission

@pytest.mark.asyncio
async def test_get_group_by_id_success(mocker):
    mongo_service = MongoDBService()
    group_id = "group-devs-id"
    group_doc = {
        "_id": group_id,
        "name": "Desenvolvedores Backend",
        "company_id": "company-id-999",
        "allowed_agents": ["agent_code_generation", "agent_refactoring", "agent_unit_tests"],
        "settings": {"max_daily_tokens": 50000, "can_create_projects": True}
    }
    mocker.patch.object(mongo_service.db.groups, "find_one", new=AsyncMock(return_value=group_doc))
    result = await mongo_service.get_group_by_id(group_id)
    assert result is not None
    assert result.id == group_id
    assert result.name == "Desenvolvedores Backend"
    assert result.company_id == "company-id-999"
    assert result.allowed_agents == ["agent_code_generation", "agent_refactoring", "agent_unit_tests"]
    assert result.settings["max_daily_tokens"] == 50000
    assert result.settings["can_create_projects"] is True

@pytest.mark.asyncio
async def test_get_group_by_id_not_found(mocker):
    mongo_service = MongoDBService()
    mocker.patch.object(mongo_service.db.groups, "find_one", new=AsyncMock(return_value=None))
    result = await mongo_service.get_group_by_id("group-nonexistent-id")
    assert result is None

@pytest.mark.asyncio
async def test_list_groups_by_company_success(mocker):
    mongo_service = MongoDBService()
    company_id = "company-id-999"
    group_docs = [
        {
            "_id": "group-devs-id",
            "name": "Desenvolvedores Backend",
            "company_id": company_id,
            "allowed_agents": ["agent_code_generation", "agent_refactoring", "agent_unit_tests"],
            "settings": {"max_daily_tokens": 50000, "can_create_projects": True}
        },
        {
            "_id": "group-qa-id",
            "name": "QA",
            "company_id": company_id,
            "allowed_agents": ["agent_unit_tests"],
            "settings": {"max_daily_tokens": 10000, "can_create_projects": False}
        }
    ]
    mock_cursor = MagicMock()
    mock_cursor.__aiter__.return_value = group_docs
    mocker.patch.object(mongo_service.db.groups, "find", return_value=mock_cursor)
    result = await mongo_service.list_groups_by_company(company_id)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].company_id == company_id
    assert result[1].company_id == company_id

@pytest.mark.asyncio
async def test_list_groups_by_company_empty(mocker):
    mongo_service = MongoDBService()
    company_id = "company-no-groups"
    mock_cursor = MagicMock()
    mock_cursor.__aiter__.return_value = []
    mocker.patch.object(mongo_service.db.groups, "find", return_value=mock_cursor)
    result = await mongo_service.list_groups_by_company(company_id)
    assert isinstance(result, list)
    assert len(result) == 0

@pytest.mark.asyncio
async def test_list_groups_by_company_invalid_company_id():
    mongo_service = MongoDBService()
    with pytest.raises(ValueError):
        await mongo_service.list_groups_by_company("")
