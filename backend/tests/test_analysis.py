import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app

client = TestClient(app)

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
@patch("backend.app.services.permission_service.PermissionService")
async def test_start_analysis_project_creation_success(mock_permission_service, mock_mongo_service):
    # Projeto não existe e usuário TEM acesso ao agente
    mock_mongo_service.return_value.db.projects.find.return_value = AsyncMock()
    mock_mongo_service.return_value.db.projects.find.return_value.__aiter__.return_value = []
    mock_permission_service.return_value.check_user_agent_access.return_value = (True, None)
    mock_mongo_service.return_value.get_user_by_email.return_value = AsyncMock()
    mock_mongo_service.return_value.get_user_by_email.return_value.id = "user123"
    mock_mongo_service.return_value.get_user_by_email.return_value.company_id = "company456"
    mock_mongo_service.return_value.create_project.return_value = True
    response = client.post(
        "/analysis/start",
        data={
            "email": "test@user.com",
            "nome_projeto": "ProjetoNovo",
            "agent_name": "agente1",
            "analysis_type": "agente1"
        }
    )
    assert response.status_code == 200
    assert "project_id" in response.json()
    assert response.json()["message"].startswith("Análise multiagente solicitada")

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
@patch("backend.app.services.permission_service.PermissionService")
async def test_start_analysis_project_creation_no_agent_access(mock_permission_service, mock_mongo_service):
    # Projeto não existe e usuário NÃO TEM acesso ao agente
    mock_mongo_service.return_value.db.projects.find.return_value = AsyncMock()
    mock_mongo_service.return_value.db.projects.find.return_value.__aiter__.return_value = []
    mock_permission_service.return_value.check_user_agent_access.return_value = (False, "Usuário não possui acesso ao agente 'agente1'.")
    response = client.post(
        "/analysis/start",
        data={
            "email": "test@user.com",
            "nome_projeto": "ProjetoNovo",
            "agent_name": "agente1",
            "analysis_type": "agente1"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Usuário não possui acesso ao agente 'agente1'."

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
@patch("backend.app.services.permission_service.PermissionService")
async def test_start_analysis_existing_project_permission_success(mock_permission_service, mock_mongo_service):
    # Projeto JÁ existe e usuário TEM permissão
    project_doc = {"_id": "projid123", "name": "ProjetoExistente"}
    mock_mongo_service.return_value.db.projects.find.return_value = AsyncMock()
    mock_mongo_service.return_value.db.projects.find.return_value.__aiter__.return_value = [project_doc]
    mock_permission_service.return_value.check_user_project_permission.return_value = (True, "owner", None)
    response = client.post(
        "/analysis/start",
        data={
            "email": "test@user.com",
            "nome_projeto": "ProjetoExistente",
            "agent_name": "agente1",
            "analysis_type": "agente1"
        }
    )
    assert response.status_code == 200
    assert "project_id" in response.json()
    assert response.json()["message"].startswith("Análise multiagente solicitada")

@pytest.mark.asyncio
@patch("backend.app.services.mongodb_service.MongoDBService")
@patch("backend.app.services.permission_service.PermissionService")
async def test_start_analysis_existing_project_permission_denied(mock_permission_service, mock_mongo_service):
    # Projeto JÁ existe e usuário NÃO TEM permissão
    project_doc = {"_id": "projid123", "name": "ProjetoExistente"}
    mock_mongo_service.return_value.db.projects.find.return_value = AsyncMock()
    mock_mongo_service.return_value.db.projects.find.return_value.__aiter__.return_value = [project_doc]
    mock_permission_service.return_value.check_user_project_permission.return_value = (False, None, "Usuário não possui permissão para executar esta ação no projeto.")
    response = client.post(
        "/analysis/start",
        data={
            "email": "test@user.com",
            "nome_projeto": "ProjetoExistente",
            "agent_name": "agente1",
            "analysis_type": "agente1"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Usuário não possui permissão para executar esta ação no projeto."
