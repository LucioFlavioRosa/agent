import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.api.analysis import router as analysis_router
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.permission_service import PermissionService
from backend.app.core.config import settings
from datetime import datetime

from main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_project_when_user_has_agent_access(monkeypatch):
    # Mock MongoDBService methods
    class MockMongoDBService:
        async def get_user_by_email(self, email):
            return type('User', (), {'id': 'user123', 'email': email, 'company_id': 'company123', 'active': True})()
        async def get_project_by_normalized_name(self, name_normalized, company_id):
            return None
        async def create_project(self, project_data):
            return True
    monkeypatch.setattr('backend.app.api.analysis.MongoDBService', lambda: MockMongoDBService())
    monkeypatch.setattr('backend.app.api.analysis.PermissionService', lambda mongo: PermissionService(mongo))
    monkeypatch.setattr('backend.app.services.permission_service.PermissionService.check_user_agent_permission', lambda self, email, agent_name: (True, None))

    response = client.post(
        '/analysis/start',
        data={
            'email': 'test@user.com',
            'nome_projeto': 'Projeto Teste',
            'agent_name': 'agentA',
            'analysis_type': 'agentA'
        }
    )
    assert response.status_code == 200
    assert 'project_id' in response.json()
    assert response.json()['message'].startswith('Análise multiagente solicitada')

@pytest.mark.asyncio
async def test_error_when_user_has_no_agent_access(monkeypatch):
    class MockMongoDBService:
        async def get_user_by_email(self, email):
            return type('User', (), {'id': 'user123', 'email': email, 'company_id': 'company123', 'active': True})()
        async def get_project_by_normalized_name(self, name_normalized, company_id):
            return None
        async def create_project(self, project_data):
            return True
    monkeypatch.setattr('backend.app.api.analysis.MongoDBService', lambda: MockMongoDBService())
    monkeypatch.setattr('backend.app.api.analysis.PermissionService', lambda mongo: PermissionService(mongo))
    monkeypatch.setattr('backend.app.services.permission_service.PermissionService.check_user_agent_permission', lambda self, email, agent_name: (False, 'Usuário não possui permissão para usar este agente.'))

    response = client.post(
        '/analysis/start',
        data={
            'email': 'test@user.com',
            'nome_projeto': 'Projeto Teste',
            'agent_name': 'agentB',
            'analysis_type': 'agentB'
        }
    )
    assert response.status_code == 403
    assert response.json()['detail'] == 'Usuário não possui permissão para usar este agente.'

@pytest.mark.asyncio
async def test_use_existing_project(monkeypatch):
    class MockMongoDBService:
        async def get_user_by_email(self, email):
            return type('User', (), {'id': 'user123', 'email': email, 'company_id': 'company123', 'active': True})()
        async def get_project_by_normalized_name(self, name_normalized, company_id):
            return {'_id': 'existing_project_id', 'name': 'Projeto Teste', 'company_id': 'company123'}
        async def create_project(self, project_data):
            return True
    monkeypatch.setattr('backend.app.api.analysis.MongoDBService', lambda: MockMongoDBService())
    monkeypatch.setattr('backend.app.api.analysis.PermissionService', lambda mongo: PermissionService(mongo))
    monkeypatch.setattr('backend.app.services.permission_service.PermissionService.check_user_agent_permission', lambda self, email, agent_name: (True, None))

    response = client.post(
        '/analysis/start',
        data={
            'email': 'test@user.com',
            'nome_projeto': 'Projeto Teste',
            'agent_name': 'agentA',
            'analysis_type': 'agentA'
        }
    )
    assert response.status_code == 200
    assert response.json()['project_id'] == 'existing_project_id'

@pytest.mark.asyncio
async def test_project_name_normalization(monkeypatch):
    class MockMongoDBService:
        async def get_user_by_email(self, email):
            return type('User', (), {'id': 'user123', 'email': email, 'company_id': 'company123', 'active': True})()
        async def get_project_by_normalized_name(self, name_normalized, company_id):
            assert name_normalized == 'projeto_teste'
            return None
        async def create_project(self, project_data):
            return True
    monkeypatch.setattr('backend.app.api.analysis.MongoDBService', lambda: MockMongoDBService())
    monkeypatch.setattr('backend.app.api.analysis.PermissionService', lambda mongo: PermissionService(mongo))
    monkeypatch.setattr('backend.app.services.permission_service.PermissionService.check_user_agent_permission', lambda self, email, agent_name: (True, None))

    response = client.post(
        '/analysis/start',
        data={
            'email': 'test@user.com',
            'nome_projeto': 'Projeto Teste',
            'agent_name': 'agentA',
            'analysis_type': 'agentA'
        }
    )
    assert response.status_code == 200
