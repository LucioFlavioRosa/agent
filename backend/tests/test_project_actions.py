import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.app.api.project_actions import router as project_actions_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(project_actions_router, prefix="/projects", tags=["Project Actions"])
client = TestClient(app)

@pytest.fixture
def mock_permission_service():
    with patch("backend.app.services.permission_service.PermissionService") as MockService:
        yield MockService

@pytest.fixture
def mock_mongo_service():
    with patch("backend.app.services.mongodb_service.MongoDBService") as MockMongo:
        yield MockMongo

# Helper para simular resposta de endpoint
async def simulate_validate_action(email, project_id, action):
    # Este helper simula chamada ao endpoint /projects/{project_id}/validate-action
    response = client.post(f"/projects/{project_id}/validate-action", json={"email": email, "action": action})
    return response

# OWNER
@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_owner_can_view(mock_check):
    mock_check.return_value = (True, "owner", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "owner@email.com", "action": "view"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "owner"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_owner_can_edit(mock_check):
    mock_check.return_value = (True, "owner", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "owner@email.com", "action": "edit"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "owner"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_owner_can_delete(mock_check):
    mock_check.return_value = (True, "owner", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "owner@email.com", "action": "delete"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "owner"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_owner_can_add_member(mock_check):
    mock_check.return_value = (True, "owner", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "owner@email.com", "action": "add_member"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "owner"

# EDITOR
@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_editor_can_view(mock_check):
    mock_check.return_value = (True, "editor", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "editor@email.com", "action": "view"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "editor"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_editor_can_edit(mock_check):
    mock_check.return_value = (True, "editor", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "editor@email.com", "action": "edit"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "editor"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_editor_cannot_delete(mock_check):
    mock_check.return_value = (False, "editor", "Usuário com role 'editor' não pode executar ação 'delete'.")
    response = client.post("/projects/proj1/validate-action", json={"email": "editor@email.com", "action": "delete"})
    assert response.status_code == 403
    assert response.json()["allowed"] is False
    assert response.json()["role"] == "editor"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_editor_cannot_add_member(mock_check):
    mock_check.return_value = (False, "editor", "Usuário com role 'editor' não pode executar ação 'add_member'.")
    response = client.post("/projects/proj1/validate-action", json={"email": "editor@email.com", "action": "add_member"})
    assert response.status_code == 403
    assert response.json()["allowed"] is False
    assert response.json()["role"] == "editor"

# VIEWER
@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_viewer_can_view(mock_check):
    mock_check.return_value = (True, "viewer", None)
    response = client.post("/projects/proj1/validate-action", json={"email": "viewer@email.com", "action": "view"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["role"] == "viewer"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_viewer_cannot_edit(mock_check):
    mock_check.return_value = (False, "viewer", "Usuário com role 'viewer' não pode executar ação 'edit'.")
    response = client.post("/projects/proj1/validate-action", json={"email": "viewer@email.com", "action": "edit"})
    assert response.status_code == 403
    assert response.json()["allowed"] is False
    assert response.json()["role"] == "viewer"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_viewer_cannot_delete(mock_check):
    mock_check.return_value = (False, "viewer", "Usuário com role 'viewer' não pode executar ação 'delete'.")
    response = client.post("/projects/proj1/validate-action", json={"email": "viewer@email.com", "action": "delete"})
    assert response.status_code == 403
    assert response.json()["allowed"] is False
    assert response.json()["role"] == "viewer"

@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_viewer_cannot_add_member(mock_check):
    mock_check.return_value = (False, "viewer", "Usuário com role 'viewer' não pode executar ação 'add_member'.")
    response = client.post("/projects/proj1/validate-action", json={"email": "viewer@email.com", "action": "add_member"})
    assert response.status_code == 403
    assert response.json()["allowed"] is False
    assert response.json()["role"] == "viewer"

# Usuário não é membro
@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_user_not_member(mock_check):
    mock_check.return_value = (False, None, "Usuário não é membro deste projeto.")
    response = client.post("/projects/proj1/validate-action", json={"email": "notmember@email.com", "action": "view"})
    assert response.status_code == 403
    assert response.json()["allowed"] is False
    assert response.json()["role"] is None

# Projeto não encontrado
@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_project_not_found(mock_check):
    mock_check.return_value = (False, None, "Projeto não encontrado.")
    response = client.post("/projects/proj_not_found/validate-action", json={"email": "owner@email.com", "action": "view"})
    assert response.status_code == 404
    assert response.json()["allowed"] is False
    assert response.json()["role"] is None

# Usuário não encontrado
@patch("backend.app.services.permission_service.PermissionService.check_user_project_action_permission", new_callable=AsyncMock)
def test_validate_action_user_not_found(mock_check):
    mock_check.return_value = (False, None, "Usuário não encontrado.")
    response = client.post("/projects/proj1/validate-action", json={"email": "user_not_found@email.com", "action": "view"})
    assert response.status_code == 404
    assert response.json()["allowed"] is False
    assert response.json()["role"] is None
