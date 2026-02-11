from backend.app.services.mongodb_service import MongoDBService
from typing import Tuple, Optional
import logging

class PermissionService:
    def __init__(self, mongo_service: Optional[MongoDBService] = None):
        self.mongo_service = mongo_service or MongoDBService()
        self.logger = logging.getLogger("PermissionService")

    async def check_user_project_permission(
        self,
        email: str,
        project_id: str,
        agent_name: str,
        action_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, None, "Usuário não encontrado."
        if not user.active:
            return False, None, "Usuário inativo."

        project = await self.mongo_service.get_project_by_id(project_id)
        if not project:
            return False, None, "Projeto não encontrado."

        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                break
        if not member_role:
            return False, None, "Usuário não possui permissão no projeto."

        groups = await self.mongo_service.get_user_groups(user.id)
        allowed_agents = set()
        for group in groups:
            allowed_agents.update(group.allowed_agents)
        if agent_name not in allowed_agents:
            return False, member_role, "Agente não permitido para o grupo do usuário."

        if action_type == "write" and member_role == "viewer":
            return False, member_role, "Usuário com role 'viewer' não pode executar ações de escrita."

        return True, member_role, None

    async def check_user_agent_access(self, email: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, f"Usuário não encontrado."
        if not user.active:
            return False, f"Usuário inativo."
        groups = await self.mongo_service.get_user_groups(user.id)
        allowed_agents = set()
        for group in groups:
            allowed_agents.update(group.allowed_agents)
        if agent_name not in allowed_agents:
            return False, f"Usuário não possui acesso ao agente '{agent_name}'."
        return True, None
