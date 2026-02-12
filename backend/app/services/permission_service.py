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
        self.logger.info(f"[check_user_project_permission] Iniciando verificação de permissão para usuário '{email}', projeto '{project_id}', agente '{agent_name}', ação '{action_type}'.")
        # 1. Busca de usuário
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não encontrado.")
            return False, None, "Usuário não encontrado."
        self.logger.info(f"[check_user_project_permission] Usuário encontrado: {user}")
        # 2. Validação de company_id
        if not user.active:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' está inativo.")
            return False, None, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não possui company_id.")
            return False, None, "Usuário não possui company_id."
        self.logger.info(f"[check_user_project_permission] company_id do usuário: {company_id}")
        # 3. Busca de projeto
        project = await self.mongo_service.get_project_by_id(project_id)
        if not project:
            self.logger.warning(f"[check_user_project_permission] Projeto '{project_id}' não encontrado.")
            return False, None, "Projeto não encontrado."
        self.logger.info(f"[check_user_project_permission] Projeto encontrado: {project}")
        # 4. Verificação de role do membro
        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                self.logger.info(f"[check_user_project_permission] Role do membro '{email}' no projeto '{project_id}': {member_role}")
                break
        if not member_role:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não possui permissão no projeto '{project_id}'.")
            return False, None, "Usuário não possui permissão no projeto."
        # 5. Busca de grupos do usuário
        groups = await self.mongo_service.get_user_groups(user.id)
        self.logger.info(f"[check_user_project_permission] Grupos do usuário '{email}': {[g.name for g in groups]}")
        # 6. Validação de agentes permitidos
        allowed_agents = set()
        for group in groups:
            if hasattr(group, "company_id") and group.company_id != company_id:
                self.logger.info(f"[check_user_project_permission] Ignorando grupo '{group.name}' por company_id diferente.")
                continue
            allowed_agents.update(group.allowed_agents)
        self.logger.info(f"[check_user_project_permission] Agentes permitidos para usuário '{email}': {allowed_agents}")
        if agent_name not in allowed_agents:
            self.logger.warning(f"[check_user_project_permission] Agente '{agent_name}' não permitido para usuário '{email}'.")
            return False, member_role, "Agente não permitido para o grupo do usuário."
        if action_type == "write" and member_role == "viewer":
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' com role 'viewer' não pode executar ações de escrita.")
            return False, member_role, "Usuário com role 'viewer' não pode executar ações de escrita."
        # 7. Resultado final da verificação de permissão
        self.logger.info(f"[check_user_project_permission] Permissão concedida para usuário '{email}' no projeto '{project_id}' com agente '{agent_name}' para ação '{action_type}'.")
        return True, member_role, None

    async def check_user_agent_permission(self, email: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"[check_user_agent_permission] Iniciando verificação de permissão de agente para usuário '{email}', agente '{agent_name}'.")
        # 1. Busca de usuário
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não encontrado.")
            return False, "Usuário não encontrado."
        self.logger.info(f"[check_user_agent_permission] Usuário encontrado: {user}")
        # 2. Validação de company_id
        if not user.active:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' está inativo.")
            return False, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não possui company_id.")
            return False, "Usuário não possui company_id."
        self.logger.info(f"[check_user_agent_permission] company_id do usuário: {company_id}")
        # 5. Busca de grupos do usuário
        groups = await self.mongo_service.get_user_groups(user.id)
        self.logger.info(f"[check_user_agent_permission] Grupos do usuário '{email}': {[g.name for g in groups]}")
        # 6. Validação de agentes permitidos
        allowed_agents = set()
        for group in groups:
            if hasattr(group, "company_id") and group.company_id != company_id:
                self.logger.info(f"[check_user_agent_permission] Ignorando grupo '{group.name}' por company_id diferente.")
                continue
            allowed_agents.update(group.allowed_agents)
        self.logger.info(f"[check_user_agent_permission] Agentes permitidos para usuário '{email}': {allowed_agents}")
        if agent_name not in allowed_agents:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não possui permissão para usar o agente '{agent_name}'.")
            return False, "Usuário não possui permissão para usar este agente."
        # 7. Resultado final da verificação de permissão
        self.logger.info(f"[check_user_agent_permission] Permissão concedida para usuário '{email}' usar agente '{agent_name}'.")
        return True, None
