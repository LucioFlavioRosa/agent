from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService
from typing import Tuple, Optional
import logging

class PermissionService:
    def __init__(self, mongo_service: Optional[MongoDBService] = None, redis_session_service: Optional[RedisSessionService] = None):
        self.mongo_service = mongo_service or MongoDBService()
        self.redis_session_service = redis_session_service or RedisSessionService()
        self.logger = logging.getLogger("PermissionService")

    @staticmethod
    def validate_project_action_by_role(role: str, action: str) -> Tuple[bool, Optional[str]]:
        """
        Valida se uma ação é permitida para uma determinada role.
        Args:
            role (str): Role do usuário ('owner', 'editor', 'viewer').
            action (str): Ação solicitada ('add_member', 'delete_project', 'edit_project', 'view_project').
        Returns:
            Tuple[bool, Optional[str]]: (permitido, mensagem de erro caso não seja)
        """
        role_action_map = {
            "owner": {"add_member", "remove_member", "delete_project", "edit_project", "view_project"},
            "editor": {"edit_project", "view_project"},
            "viewer": {"view_project"}
        }
        allowed_actions = role_action_map.get(role)
        if allowed_actions is None:
            return False, f"Role desconhecida: '{role}'."
        if action not in allowed_actions:
            return False, f"Ação '{action}' não permitida para role '{role}'."
        return True, None

    async def check_user_can_create_project(self, email: str, company_id: str) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"[check_user_can_create_project] Validando criação para: {email} na empresa: {company_id}")
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, "Usuário não encontrado."
        user_actual_company = getattr(user, "company_id", None)
        if user_actual_company != company_id:
            self.logger.error(f"[Security] Conflito de empresa: Usuário {email} pertence a {user_actual_company}, mas tentou ação em {company_id}")
            return False, "Acesso negado: Divergência de organização."
        groups = await self.mongo_service.get_user_groups(user.id)
        for group in groups:
            group_company = getattr(group, "company_id", None) or group.get("company_id")
            if group_company != company_id:
                continue
            group_settings = getattr(group, "settings", {}) if hasattr(group, "settings") else group.get("settings", {})
            if group_settings.get("can_create_projects") is True:
                self.logger.info(f"Permissão de criação confirmada via grupo '{getattr(group, 'name', 'N/A')}' para empresa {company_id}")
                return True, None
        return False, "O usuário não tem permissão para criar novos projetos nesta empresa. Verifique as configurações de grupo."

    async def check_user_project_permission(
        self,
        email: str,
        project_id: str,
        agent_name: str,
        action_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        self.logger.info(f"[check_user_project_permission] Iniciando verificação de permissão para usuário '{email}', projeto '{project_id}', agente '{agent_name}', ação '{action_type}'.")
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não encontrado.")
            return False, None, "Usuário não encontrado."
        if not user.active:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' está inativo.")
            return False, None, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não possui company_id.")
            return False, None, "Usuário não possui company_id."
        self.logger.info(f"[check_user_project_permission] company_id do usuário: {company_id}")

        # --- CACHE DE PERMISSÕES NO REDIS ---
        permissions = self.redis_session_service.get_user_permissions(email, company_id)
        if permissions:
            self.logger.info(f"[check_user_project_permission] Permissões encontradas no cache Redis para {email}:{company_id}")
            # Validação de projeto
            project_perm = permissions.get("project_permissions", {}).get(project_id)
            if not project_perm:
                self.logger.warning(f"[check_user_project_permission] Projeto '{project_id}' não encontrado no cache de permissões.")
                return False, None, "Projeto não encontrado."
            member_role = project_perm.get("role")
            if not member_role:
                self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não possui permissão no projeto '{project_id}' (cache).")
                return False, None, "Usuário não possui permissão no projeto."
            permitted, error_msg = self.validate_project_action_by_role(member_role, action_type)
            if not permitted:
                self.logger.warning(f"[check_user_project_permission] {error_msg}")
                return False, member_role, error_msg
            allowed_agents = permissions.get("allowed_agents", set())
            if agent_name not in allowed_agents:
                self.logger.warning(f"[check_user_project_permission] Agente '{agent_name}' não permitido para usuário '{email}' (cache).")
                return False, member_role, "Agente não permitido para o grupo do usuário."
            self.logger.info(f"[check_user_project_permission] Permissão concedida via cache para usuário '{email}' no projeto '{project_id}' com agente '{agent_name}' para ação '{action_type}'.")
            return True, member_role, None
        # --- FIM CACHE ---

        # Busca de projeto no MongoDB
        project = await self.mongo_service.get_project_by_id(project_id)
        if not project:
            self.logger.warning(f"[check_user_project_permission] Projeto '{project_id}' não encontrado.")
            return False, None, "Projeto não encontrado."
        if getattr(project, "company_id", None) != company_id:
            self.logger.error(f"[Security] Usuário {email} tentou acessar projeto {project_id} de outra empresa!")
            return False, None, "Acesso negado: O projeto pertence a outra organização."
        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                self.logger.info(f"[check_user_project_permission] Role do membro '{email}' no projeto '{project_id}': {member_role}")
                break
        if not member_role:
            self.logger.warning(f"[check_user_project_permission] Usuário '{email}' não está na lista de membros do projeto '{project_id}'.")
            return False, None, "Usuário não está na lista de membros do projeto."
        permitted, error_msg = self.validate_project_action_by_role(member_role.lower(), action_type)
        if not permitted:
            self.logger.warning(f"[check_user_project_permission] {error_msg}")
            return False, member_role, error_msg
        groups = await self.mongo_service.get_user_groups(user.id)
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
        # --- Construção e armazenamento do mapa de permissões ---
        project_permissions = {}
        project_permissions[project_id] = {
            "role": member_role,
            "actions": list(self.validate_project_action_by_role(member_role.lower(), action_type)[0] and [action_type] or [])
        }
        permissions_dict = {
            "allowed_agents": list(allowed_agents),
            "project_permissions": project_permissions
        }
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[check_user_project_permission] Permissões armazenadas no Redis para {email}:{company_id}")
        self.logger.info(f"[check_user_project_permission] Permissão concedida para usuário '{email}' no projeto '{project_id}' com agente '{agent_name}' para ação '{action_type}'.")
        return True, member_role, None

    async def check_user_agent_permission(self, email: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"[check_user_agent_permission] Iniciando verificação de permissão de agente para usuário '{email}', agente '{agent_name}'.")
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não encontrado.")
            return False, "Usuário não encontrado."
        if not user.active:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' está inativo.")
            return False, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não possui company_id.")
            return False, "Usuário não possui company_id."
        self.logger.info(f"[check_user_agent_permission] company_id do usuário: {company_id}")

        # --- CACHE DE PERMISSÕES NO REDIS ---
        permissions = self.redis_session_service.get_user_permissions(email, company_id)
        if permissions:
            self.logger.info(f"[check_user_agent_permission] Permissões encontradas no cache Redis para {email}:{company_id}")
            allowed_agents = permissions.get("allowed_agents", set())
            if agent_name not in allowed_agents:
                self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não possui permissão para usar o agente '{agent_name}' (cache).")
                return False, "Usuário não possui permissão para usar este agente."
            self.logger.info(f"[check_user_agent_permission] Permissão concedida via cache para usuário '{email}' usar agente '{agent_name}'.")
            return True, None
        # --- FIM CACHE ---

        groups = await self.mongo_service.get_user_groups(user.id)
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
        # --- Construção e armazenamento do mapa de permissões ---
        permissions_dict = {
            "allowed_agents": list(allowed_agents),
            "project_permissions": {}
        }
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[check_user_agent_permission] Permissões armazenadas no Redis para {email}:{company_id}")
        self.logger.info(f"[check_user_agent_permission] Permissão concedida para usuário '{email}' usar agente '{agent_name}'.")
        return True, None

    async def check_user_project_action_permission(
        self,
        email: str,
        project_id: str,
        action_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        self.logger.info(f"[check_user_project_action_permission] Iniciando validação de permissão para usuário '{email}' no projeto '{project_id}' para ação '{action_type}'.")
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[check_user_project_action_permission] Usuário '{email}' não encontrado.")
            return False, None, "Usuário não encontrado."
        if not user.active:
            self.logger.warning(f"[check_user_project_action_permission] Usuário '{email}' está inativo.")
            return False, None, "Usuário inativo."
        company_id = getattr(user, "company_id", None)
        if not company_id:
            self.logger.warning(f"[check_user_project_action_permission] Usuário '{email}' não possui company_id.")
            return False, None, "Usuário não possui company_id."
        self.logger.info(f"[check_user_project_action_permission] company_id do usuário: {company_id}")

        # --- CACHE DE PERMISSÕES NO REDIS ---
        permissions = self.redis_session_service.get_user_permissions(email, company_id)
        if permissions:
            self.logger.info(f"[check_user_project_action_permission] Permissões encontradas no cache Redis para {email}:{company_id}")
            project_perm = permissions.get("project_permissions", {}).get(project_id)
            if not project_perm:
                self.logger.warning(f"[check_user_project_action_permission] Projeto '{project_id}' não encontrado no cache de permissões.")
                return False, None, "Projeto não encontrado."
            member_role = project_perm.get("role")
            if not member_role:
                self.logger.warning(f"[check_user_project_action_permission] Usuário '{email}' não possui permissão no projeto '{project_id}' (cache).")
                return False, None, "Usuário não possui permissão no projeto."
            permitted, error_msg = self.validate_project_action_by_role(member_role.lower(), action_type)
            if not permitted:
                self.logger.warning(f"[check_user_project_action_permission] {error_msg}")
                return False, member_role, error_msg
            self.logger.info(f"[check_user_project_action_permission] Permissão concedida via cache para usuário '{email}' no projeto '{project_id}' para ação '{action_type}'.")
            return True, member_role, None
        # --- FIM CACHE ---

        project = await self.mongo_service.get_project_by_id(project_id)
        if getattr(project, "company_id", None) != company_id:
            self.logger.error(f"[Security] Usuário {email} tentou acessar projeto {project_id} de outra empresa!")
            return False, None, "Acesso negado: O projeto pertence a outra organização."
        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                self.logger.info(f"[check_user_project_action_permission] Role do membro '{email}' no projeto '{project_id}': {member_role}")
                break
        if not member_role:
            self.logger.warning(f"[check_user_project_action_permission] Usuário '{email}' não está na lista de membros do projeto '{project_id}'.")
            return False, None, "Usuário não está na lista de membros do projeto."
        permitted, error_msg = self.validate_project_action_by_role(member_role.lower(), action_type)
        if not permitted:
            self.logger.warning(f"[check_user_project_action_permission] {error_msg}")
            return False, member_role, error_msg
        # --- Construção e armazenamento do mapa de permissões ---
        project_permissions = {}
        project_permissions[project_id] = {
            "role": member_role,
            "actions": list(self.validate_project_action_by_role(member_role.lower(), action_type)[0] and [action_type] or [])
        }
        permissions_dict = {
            "allowed_agents": [],
            "project_permissions": project_permissions
        }
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[check_user_project_action_permission] Permissões armazenadas no Redis para {email}:{company_id}")
        self.logger.info(f"[check_user_project_action_permission] Permissão concedida para usuário '{email}' no projeto '{project_id}' para ação '{action_type}'.")
        return True, member_role, None
