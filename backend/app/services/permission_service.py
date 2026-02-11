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
        company_id = getattr(user, "company_id", None)
        if not company_id:
            return False, None, "Usuário não possui company_id."

        # Passa company_id para buscas subsequentes se necessário
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

        # Busca grupos do usuário considerando company_id
        groups = await self.mongo_service.get_user_groups(user.id)
        allowed_agents = set()
        for group in groups:
            # Se o grupo tiver company_id, valida se corresponde ao do usuário
            if hasattr(group, "company_id") and group.company_id != company_id:
                continue
            allowed_agents.update(group.allowed_agents)
        if agent_name not in allowed_agents:
            return False, member_role, "Agente não permitido para o grupo do usuário."

        if action_type == "write" and member_role == "viewer":
            return False, member_role, "Usuário com role 'viewer' não pode executar ações de escrita."

        return True, member_role, None

    async def check_user_agent_permission(self, email: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se o usuário tem permissão para usar o agente especificado.
        Retorna (True, None) se permitido, ou (False, mensagem_erro) caso contrário.
        """
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, "Usuário não encontrado."
        if not user.active:
            return False, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            return False, "Usuário não possui company_id."
        groups = await self.mongo_service.get_user_groups(user.id)
        allowed_agents = set()
        for group in groups:
            if hasattr(group, "company_id") and group.company_id != company_id:
                continue
            allowed_agents.update(group.allowed_agents)
        if agent_name not in allowed_agents:
            return False, "Usuário não possui permissão para usar este agente."
        return True, None
