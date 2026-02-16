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

    async def _build_complete_permissions(self, email: str, company_id: str) -> dict:
        # Busca todos os projetos do usuário
        projects = await self.mongo_service.get_user_projects_with_access(email)
        project_permissions = {}
        for proj in projects:
            proj_id = proj.get("project_id")
            role = proj.get("role")
            actions = []
            if role:
                # Adiciona todas ações permitidas para a role
                if role == "owner":
                    actions = ["add_member", "remove_member", "delete_project", "edit_project", "view_project"]
                elif role == "editor":
                    actions = ["edit_project", "view_project"]
                elif role == "viewer":
                    actions = ["view_project"]
            project_permissions[proj_id] = {
                "role": role,
                "actions": actions
            }
        # Busca todos agentes permitidos via grupos
        user = await self.mongo_service.get_user_by_email(email)
        allowed_agents = set()
        if user and hasattr(user, "group_ids"):
            for group_id in user.group_ids:
                group = await self.mongo_service.get_group_by_id(group_id)
                if group and hasattr(group, "allowed_agents"):
                    allowed_agents.update(group.allowed_agents)
        return {
            "allowed_agents": list(allowed_agents),
            "project_permissions": project_permissions
        }

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
        # --- Construção e armazenamento do mapa de permissões completo ---
        permissions_dict = await self._build_complete_permissions(email, company_id)
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[check_user_project_permission] Permissões completas armazenadas no Redis para {email}:{company_id}")
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

        # --- Construção e armazenamento do mapa de permissões completo ---
        permissions_dict = await self._build_complete_permissions(email, company_id)
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        allowed_agents = permissions_dict.get("allowed_agents", [])
        self.logger.info(f"[check_user_agent_permission] Permissões completas armazenadas no Redis para {email}:{company_id}")
        if agent_name not in allowed_agents:
            self.logger.warning(f"[check_user_agent_permission] Usuário '{email}' não possui permissão para usar o agente '{agent_name}'.")
            return False, "Usuário não possui permissão para usar este agente."
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
        # --- Construção e armazenamento do mapa de permissões completo ---
        permissions_dict = await self._build_complete_permissions(email, company_id)
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[check_user_project_action_permission] Permissões completas armazenadas no Redis para {email}:{company_id}")
        self.logger.info(f"[check_user_project_action_permission] Permissão concedida para usuário '{email}' no projeto '{project_id}' para ação '{action_type}'.")
        return True, member_role, None

# Adicione este método à classe PermissionService
    async def check_user_can_create_project(self, email: str, company_id: str) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"[check_user_can_create_project] Verificando permissão de criação para '{email}'.")
        
        # 1. Busca o usuário
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, "Usuário não encontrado."
            
        # 2. Verifica se o usuário tem grupos
        if not hasattr(user, "group_ids") or not user.group_ids:
            # Se não tem grupo, assumimos False (segurança por padrão) ou True dependendo da sua regra de negócio.
            # Aqui estou assumindo que sem grupo = sem permissão especial.
            return False, "Usuário não pertence a nenhum grupo com permissão de criação."

        # 3. Itera sobre os grupos para achar a flag 'can_create_projects'
        can_create = False
        
        for group_id in user.group_ids:
            group = await self.mongo_service.get_group_by_id(group_id)
            if group and hasattr(group, "settings"):
                # Busca a chave 'can_create_projects' dentro de settings
                # Exemplo de settings: {"max_daily_tokens": 100000, "can_create_projects": True}
                settings_dict = group.settings if isinstance(group.settings, dict) else group.settings.dict()
                
                if settings_dict.get("can_create_projects") is True:
                    can_create = True
                    self.logger.info(f"[check_user_can_create_project] Permissão concedida pelo grupo '{group.name}'.")
                    break
        
        if can_create:
            return True, None
        else:
            return False, "Seu grupo de usuário não tem permissão para criar novos projetos."
