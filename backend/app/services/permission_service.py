from backend.app.services.mongodb_service import MongoDBService
from typing import Tuple, Optional
import logging
from backend.app.utils import logger_utils

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
        logger_utils.log_validation_step("check_user_project_permission", {
            "email": email,
            "project_id": project_id,
            "agent_name": agent_name,
            "action_type": action_type
        })
        user = await self.mongo_service.get_user_by_email(email)
        logger_utils.log_service_call("MongoDBService.get_user_by_email", {
            "email": email,
            "user_found": bool(user)
        })
        if not user:
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Usuário não encontrado."
            })
            return False, None, "Usuário não encontrado."
        if not user.active:
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Usuário inativo."
            })
            return False, None, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Usuário não possui company_id."
            })
            return False, None, "Usuário não possui company_id."

        project = await self.mongo_service.get_project_by_id(project_id)
        logger_utils.log_service_call("MongoDBService.get_project_by_id", {
            "project_id": project_id,
            "project_found": bool(project)
        })
        if not project:
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Projeto não encontrado."
            })
            return False, None, "Projeto não encontrado."

        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                break
        logger_utils.log_validation_step("Role validation", {
            "email": email,
            "member_role": member_role
        })
        if not member_role:
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Usuário não possui permissão no projeto."
            })
            return False, None, "Usuário não possui permissão no projeto."

        groups = await self.mongo_service.get_user_groups(user.id)
        logger_utils.log_service_call("MongoDBService.get_user_groups", {
            "user_id": user.id,
            "groups_count": len(groups)
        })
        allowed_agents = set()
        for group in groups:
            if hasattr(group, "company_id") and group.company_id != company_id:
                continue
            allowed_agents.update(group.allowed_agents)
        logger_utils.log_validation_step("Agent permission validation", {
            "agent_name": agent_name,
            "allowed_agents": list(allowed_agents)
        })
        if agent_name not in allowed_agents:
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Agente não permitido para o grupo do usuário."
            })
            return False, member_role, "Agente não permitido para o grupo do usuário."

        if action_type == "write" and member_role == "viewer":
            logger_utils.log_response_sent("check_user_project_permission", {
                "success": False,
                "reason": "Usuário com role 'viewer' não pode executar ações de escrita."
            })
            return False, member_role, "Usuário com role 'viewer' não pode executar ações de escrita."

        logger_utils.log_response_sent("check_user_project_permission", {
            "success": True,
            "member_role": member_role,
            "reason": None
        })
        return True, member_role, None

    async def check_user_agent_permission(self, email: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        logger_utils.log_validation_step("check_user_agent_permission", {
            "email": email,
            "agent_name": agent_name
        })
        user = await self.mongo_service.get_user_by_email(email)
        logger_utils.log_service_call("MongoDBService.get_user_by_email", {
            "email": email,
            "user_found": bool(user)
        })
        if not user:
            logger_utils.log_response_sent("check_user_agent_permission", {
                "success": False,
                "reason": "Usuário não encontrado."
            })
            return False, "Usuário não encontrado."
        if not user.active:
            logger_utils.log_response_sent("check_user_agent_permission", {
                "success": False,
                "reason": "Usuário inativo."
            })
            return False, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            logger_utils.log_response_sent("check_user_agent_permission", {
                "success": False,
                "reason": "Usuário não possui company_id."
            })
            return False, "Usuário não possui company_id."
        groups = await self.mongo_service.get_user_groups(user.id)
        logger_utils.log_service_call("MongoDBService.get_user_groups", {
            "user_id": user.id,
            "groups_count": len(groups)
        })
        allowed_agents = set()
        for group in groups:
            if hasattr(group, "company_id") and group.company_id != company_id:
                continue
            allowed_agents.update(group.allowed_agents)
        logger_utils.log_validation_step("Agent permission validation", {
            "agent_name": agent_name,
            "allowed_agents": list(allowed_agents)
        })
        if agent_name not in allowed_agents:
            logger_utils.log_response_sent("check_user_agent_permission", {
                "success": False,
                "reason": "Usuário não possui permissão para usar este agente."
            })
            return False, "Usuário não possui permissão para usar este agente."
        logger_utils.log_response_sent("check_user_agent_permission", {
            "success": True,
            "reason": None
        })
        return True, None
