from backend.app.services.mongodb_service import MongoDBService
from typing import Tuple, Optional

class PermissionService:
    def __init__(self, mongo_service: Optional[MongoDBService] = None):
        self.mongo_service = mongo_service or MongoDBService()

    async def validate_user_agent_permission(self, email: str, project_id: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        user = await self.mongo_service.get_user_by_email(email)
        if not user or not user.active:
            return False, None
        role = await self.mongo_service.check_user_project_permission(user.id, project_id)
        if not role:
            return False, None
        groups = await self.mongo_service.get_user_groups(user.id)
        allowed_agents = set()
        for group in groups:
            allowed_agents.update(group.allowed_agents)
        if agent_name not in allowed_agents:
            return False, role
        # Se chegou aqui, usuário tem permissão
        return True, role
