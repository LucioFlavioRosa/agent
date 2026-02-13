import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.permission_service import PermissionService

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_owner_view(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "owner@email.com", "active": True, "company_id": "comp1", "id": "u1"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "owner@email.com", "role": "owner"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("owner@email.com", "proj1", "view")
    assert allowed is True
    assert role == "owner"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_owner_edit(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "owner@email.com", "active": True, "company_id": "comp1", "id": "u1"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "owner@email.com", "role": "owner"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("owner@email.com", "proj1", "edit")
    assert allowed is True
    assert role == "owner"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_owner_delete(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "owner@email.com", "active": True, "company_id": "comp1", "id": "u1"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "owner@email.com", "role": "owner"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("owner@email.com", "proj1", "delete")
    assert allowed is True
    assert role == "owner"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_owner_add_member(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "owner@email.com", "active": True, "company_id": "comp1", "id": "u1"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "owner@email.com", "role": "owner"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("owner@email.com", "proj1", "add_member")
    assert allowed is True
    assert role == "owner"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_editor_view(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "editor@email.com", "active": True, "company_id": "comp1", "id": "u2"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "editor@email.com", "role": "editor"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("editor@email.com", "proj1", "view")
    assert allowed is True
    assert role == "editor"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_editor_edit(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "editor@email.com", "active": True, "company_id": "comp1", "id": "u2"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "editor@email.com", "role": "editor"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("editor@email.com", "proj1", "edit")
    assert allowed is True
    assert role == "editor"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_editor_delete(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "editor@email.com", "active": True, "company_id": "comp1", "id": "u2"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "editor@email.com", "role": "editor"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("editor@email.com", "proj1", "delete")
    assert allowed is False
    assert role == "editor"
    assert error == "Usuário com role 'editor' não pode executar ação 'delete'."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_editor_add_member(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "editor@email.com", "active": True, "company_id": "comp1", "id": "u2"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "editor@email.com", "role": "editor"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("editor@email.com", "proj1", "add_member")
    assert allowed is False
    assert role == "editor"
    assert error == "Usuário com role 'editor' não pode executar ação 'add_member'."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_viewer_view(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "viewer@email.com", "active": True, "company_id": "comp1", "id": "u3"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "viewer@email.com", "role": "viewer"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("viewer@email.com", "proj1", "view")
    assert allowed is True
    assert role == "viewer"
    assert error is None

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_viewer_edit(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "viewer@email.com", "active": True, "company_id": "comp1", "id": "u3"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "viewer@email.com", "role": "viewer"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("viewer@email.com", "proj1", "edit")
    assert allowed is False
    assert role == "viewer"
    assert error == "Usuário com role 'viewer' não pode executar ação 'edit'."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_viewer_delete(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "viewer@email.com", "active": True, "company_id": "comp1", "id": "u3"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "viewer@email.com", "role": "viewer"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("viewer@email.com", "proj1", "delete")
    assert allowed is False
    assert role == "viewer"
    assert error == "Usuário com role 'viewer' não pode executar ação 'delete'."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_viewer_add_member(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "viewer@email.com", "active": True, "company_id": "comp1", "id": "u3"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "viewer@email.com", "role": "viewer"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("viewer@email.com", "proj1", "add_member")
    assert allowed is False
    assert role == "viewer"
    assert error == "Usuário com role 'viewer' não pode executar ação 'add_member'."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_user_not_member(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "notmember@email.com", "active": True, "company_id": "comp1", "id": "u4"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "owner@email.com", "role": "owner"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("notmember@email.com", "proj1", "view")
    assert allowed is False
    assert role is None
    assert error == "Usuário não é membro deste projeto."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_project_not_found(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=type("User", (), {"email": "owner@email.com", "active": True, "company_id": "comp1", "id": "u1"})())
    mock_mongo.get_project_by_id = AsyncMock(return_value=None)
    allowed, role, error = await service.check_user_project_action_permission("owner@email.com", "proj_not_found", "view")
    assert allowed is False
    assert role is None
    assert error == "Projeto não encontrado."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
async def test_check_user_project_action_permission_user_not_found(mock_mongo):
    service = PermissionService(mock_mongo)
    mock_mongo.get_user_by_email = AsyncMock(return_value=None)
    mock_mongo.get_project_by_id = AsyncMock(return_value=type("Project", (), {"members": [type("Member", (), {"email": "owner@email.com", "role": "owner"})()]})())
    allowed, role, error = await service.check_user_project_action_permission("user_not_found@email.com", "proj1", "view")
    assert allowed is False
    assert role is None
    assert error == "Usuário não encontrado."
