import pytest
from unittest.mock import AsyncMock, MagicMock

class PermissionService:
    def __init__(self, db):
        self.db = db

    async def can_execute_action(self, user_email, project_id, agent_name, action_type):
        # Busca usuário
        user = await self.db.users.find_one({"email": user_email})
        if not user or not user.get("active", True):
            return (False, 403, "Usuário não encontrado ou inativo.")
        # Busca projeto
        project = await self.db.projects.find_one({"_id": project_id})
        if not project:
            return (False, 403, "Projeto não encontrado.")
        # Busca membro
        member = next((m for m in project.get("members", []) if m["email"] == user_email), None)
        if not member:
            return (False, 403, "Usuário não possui permissão no projeto.")
        role = member["role"]
        # Busca grupos
        group_ids = user.get("group_ids", [])
        groups = await self.db.groups.find({"_id": {"$in": group_ids}}).to_list(length=None)
        allowed_agents = set()
        for g in groups:
            allowed_agents.update(g.get("allowed_agents", []))
        if agent_name not in allowed_agents:
            return (False, 403, "Agente não permitido para o grupo do usuário.")
        # Verifica ação
        if action_type == "write" and role == "viewer":
            return (False, 403, "Usuário com role 'viewer' não pode executar ações de escrita.")
        return (True, 200, "Permissão concedida.")

@pytest.mark.asyncio
async def test_owner_can_execute_any_action():
    db = MagicMock()
    db.users.find_one = AsyncMock(return_value={"email": "owner@empresa.com", "active": True, "group_ids": ["group-devs-id"]})
    db.projects.find_one = AsyncMock(return_value={"_id": "project-id-555", "members": [{"email": "owner@empresa.com", "role": "owner"}]})
    db.groups.find = MagicMock()
    db.groups.find.return_value.to_list = AsyncMock(return_value=[{"_id": "group-devs-id", "allowed_agents": ["agent_code_generation", "agent_refactoring"]}])
    service = PermissionService(db)
    allowed, code, msg = await service.can_execute_action("owner@empresa.com", "project-id-555", "agent_code_generation", "write")
    assert allowed is True
    assert code == 200
    assert msg == "Permissão concedida."

@pytest.mark.asyncio
async def test_viewer_cannot_execute_write_action():
    db = MagicMock()
    db.users.find_one = AsyncMock(return_value={"email": "viewer@empresa.com", "active": True, "group_ids": ["group-devs-id"]})
    db.projects.find_one = AsyncMock(return_value={"_id": "project-id-555", "members": [{"email": "viewer@empresa.com", "role": "viewer"}]})
    db.groups.find = MagicMock()
    db.groups.find.return_value.to_list = AsyncMock(return_value=[{"_id": "group-devs-id", "allowed_agents": ["agent_code_generation"]}])
    service = PermissionService(db)
    allowed, code, msg = await service.can_execute_action("viewer@empresa.com", "project-id-555", "agent_code_generation", "write")
    assert allowed is False
    assert code == 403
    assert "viewer" in msg

@pytest.mark.asyncio
async def test_user_without_permission_in_project_gets_403():
    db = MagicMock()
    db.users.find_one = AsyncMock(return_value={"email": "noaccess@empresa.com", "active": True, "group_ids": ["group-devs-id"]})
    db.projects.find_one = AsyncMock(return_value={"_id": "project-id-555", "members": [{"email": "other@empresa.com", "role": "owner"}]})
    db.groups.find = MagicMock()
    db.groups.find.return_value.to_list = AsyncMock(return_value=[{"_id": "group-devs-id", "allowed_agents": ["agent_code_generation"]}])
    service = PermissionService(db)
    allowed, code, msg = await service.can_execute_action("noaccess@empresa.com", "project-id-555", "agent_code_generation", "write")
    assert allowed is False
    assert code == 403
    assert "não possui permissão" in msg

@pytest.mark.asyncio
async def test_agent_not_allowed_for_group_returns_403():
    db = MagicMock()
    db.users.find_one = AsyncMock(return_value={"email": "dev@empresa.com", "active": True, "group_ids": ["group-devs-id"]})
    db.projects.find_one = AsyncMock(return_value={"_id": "project-id-555", "members": [{"email": "dev@empresa.com", "role": "owner"}]})
    db.groups.find = MagicMock()
    db.groups.find.return_value.to_list = AsyncMock(return_value=[{"_id": "group-devs-id", "allowed_agents": ["agent_code_generation"]}])
    service = PermissionService(db)
    allowed, code, msg = await service.can_execute_action("dev@empresa.com", "project-id-555", "agent_infra_deploy", "write")
    assert allowed is False
    assert code == 403
    assert "Agente não permitido" in msg
