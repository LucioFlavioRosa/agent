import pytest
import mongomock
from pymongo import MongoClient
from backend.app.services.mongodb_service import MongoDBService

@pytest.fixture(scope="module")
def mongo_mock():
    client = mongomock.MongoClient()
    db = client["test_db"]
    # Setup collections
    users = db["users"]
    groups = db["groups"]
    projects = db["projects"]
    # Insert mock data
    users.insert_one({
        "_id": "user-id-001",
        "email": "joao.silva@empresa.com",
        "name": "João Silva",
        "company_id": "company-id-999",
        "active": True,
        "group_ids": ["group-devs-id", "group-admins-id"],
        "created_at": "2026-02-10T10:00:00Z"
    })
    groups.insert_one({
        "_id": "group-devs-id",
        "name": "Desenvolvedores Backend",
        "company_id": "company-id-999",
        "allowed_agents": [
            "agent_code_generation",
            "agent_refactoring",
            "agent_unit_tests"
        ],
        "settings": {
            "max_daily_tokens": 50000,
            "can_create_projects": True
        }
    })
    projects.insert_one({
        "_id": "project-id-555",
        "name": "Migração Legacy SAP",
        "description": "Projeto de modernização...",
        "company_id": "company-id-999",
        "blob_path": "projects/project-id-555/",
        "members": [
            {
                "user_id": "user-id-001",
                "email": "joao.silva@empresa.com",
                "role": "owner",
                "added_at": "2026-02-10T14:00:00Z"
            },
            {
                "user_id": "user-id-002",
                "email": "maria@empresa.com",
                "role": "viewer",
                "added_at": "2026-02-10T14:10:00Z"
            }
        ],
        "created_at": "2026-02-10T14:00:00Z",
        "updated_at": "2026-02-10T15:30:00Z"
    })
    return db

@pytest.fixture(scope="module")
def mongodb_service(mongo_mock):
    return MongoDBService(db=mongo_mock)

def test_buscar_usuario_por_email(mongodb_service):
    user = mongodb_service.get_user_by_email("joao.silva@empresa.com")
    assert user is not None
    assert user["name"] == "João Silva"
    assert user["active"] is True

def test_buscar_grupos_do_usuario(mongodb_service):
    user = mongodb_service.get_user_by_email("joao.silva@empresa.com")
    group_ids = user["group_ids"]
    groups = [mongodb_service.get_group_by_id(gid) for gid in group_ids]
    assert len(groups) == 2
    assert any(g["name"] == "Desenvolvedores Backend" for g in groups)

def test_buscar_agentes_permitidos_para_grupo(mongodb_service):
    group = mongodb_service.get_group_by_id("group-devs-id")
    allowed_agents = group["allowed_agents"]
    assert "agent_code_generation" in allowed_agents
    assert "agent_infra_deploy" not in allowed_agents

def test_verificar_permissao_usuario_em_projeto(mongodb_service):
    project = mongodb_service.get_project_by_id("project-id-555")
    members = project["members"]
    joao = next((m for m in members if m["email"] == "joao.silva@empresa.com"), None)
    maria = next((m for m in members if m["email"] == "maria@empresa.com"), None)
    assert joao["role"] == "owner"
    assert maria["role"] == "viewer"
