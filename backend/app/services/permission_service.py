from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService
from typing import Tuple, Optional, Set, List
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
        """
        Constrói o dicionário completo de permissões buscando do Mongo.
        """
        # Busca todos os projetos do usuário
        projects = await self.mongo_service.get_user_projects_with_access(email)
        project_permissions = {}
        for proj in projects:
            proj_id = proj.get("project_id")
            role = proj.get("role")
            actions = []
            if role:
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

    async def _resolve_project_access(
        self, 
        email: str, 
        project_id: str, 
        action_type: str
    ) -> Tuple[bool, Optional[str], Optional[Set[str]], Optional[str]]:
        """
        Método centralizado para verificar acesso a projeto.
        Realiza: Validação de Usuário -> Check Cache -> Fallback Mongo -> Salva Cache.
        
        Retorna: (is_success, role, allowed_agents_set, error_message)
        """
        self.logger.info(f"[_resolve_project_access] Verificando acesso: User '{email}', Proj '{project_id}', Action '{action_type}'")

        # 1. Validação do Usuário
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[_resolve_project_access] Usuário '{email}' não encontrado.")
            return False, None, None, "Usuário não encontrado."
        if not user.active:
            self.logger.warning(f"[_resolve_project_access] Usuário '{email}' está inativo.")
            return False, None, None, "Usuário inativo."
        
        company_id = getattr(user, "company_id", None)
        if not company_id:
            self.logger.warning(f"[_resolve_project_access] Usuário '{email}' não possui company_id.")
            return False, None, None, "Usuário não possui company_id."

        # 2. Verifica Cache (Redis)
        permissions = self.redis_session_service.get_user_permissions(email, company_id)
        if permissions:
            self.logger.info(f"[_resolve_project_access] Cache hit para {email}:{company_id}")
            project_perm = permissions.get("project_permissions", {}).get(project_id)
            
            if not project_perm:
                self.logger.warning(f"[_resolve_project_access] Projeto '{project_id}' não encontrado no cache.")
                return False, None, None, "Projeto não encontrado."
            
            member_role = project_perm.get("role")
            if not member_role:
                return False, None, None, "Usuário não possui permissão no projeto."

            # Valida Role vs Ação
            permitted, error_msg = self.validate_project_action_by_role(member_role.lower(), action_type)
            if not permitted:
                self.logger.warning(f"[_resolve_project_access] {error_msg}")
                return False, member_role, None, error_msg
            
            allowed_agents = set(permissions.get("allowed_agents", []))
            return True, member_role, allowed_agents, None

        # 3. Cache Miss - Busca no Mongo
        self.logger.info(f"[_resolve_project_access] Cache miss. Buscando dados no Mongo.")
        project = await self.mongo_service.get_project_by_id(project_id)
        
        if not project:
            self.logger.warning(f"[_resolve_project_access] Projeto '{project_id}' não encontrado no Mongo.")
            return False, None, None, "Projeto não encontrado."
        
        if getattr(project, "company_id", None) != company_id:
            self.logger.error(f"[Security] Usuário {email} tentou acessar projeto {project_id} de outra empresa!")
            return False, None, None, "Acesso negado: O projeto pertence a outra organização."

        member_role = None
        for member in project.members:
            if member.email == email:
                member_role = member.role
                break
        
        if not member_role:
            self.logger.warning(f"[_resolve_project_access] Usuário '{email}' não é membro do projeto '{project_id}'.")
            return False, None, None, "Usuário não está na lista de membros do projeto."

        # Valida Role vs Ação
        permitted, error_msg = self.validate_project_action_by_role(member_role.lower(), action_type)
        if not permitted:
            self.logger.warning(f"[_resolve_project_access] {error_msg}")
            return False, member_role, None, error_msg

        # Reconstrói permissões completas e salva no Cache
        permissions_dict = await self._build_complete_permissions(email, company_id)
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[_resolve_project_access] Permissões atualizadas no Redis.")

        allowed_agents = set(permissions_dict.get("allowed_agents", []))
        return True, member_role, allowed_agents, None

    # -------------------------------------------------------------------------
    # MÉTODOS PÚBLICOS
    # -------------------------------------------------------------------------

    async def check_user_project_permission(
        self,
        email: str,
        project_id: str,
        agent_name: str,
        action_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifica se o usuário pode executar uma ação no projeto E se tem acesso ao agente especificado.
        """
        success, role, allowed_agents, error_msg = await self._resolve_project_access(email, project_id, action_type)
        
        if not success:
            return False, role, error_msg

        # Verificação adicional específica deste método: Agente
        if agent_name not in allowed_agents:
            self.logger.warning(f"[check_user_project_permission] Agente '{agent_name}' não permitido para usuário '{email}'.")
            return False, role, "Agente não permitido para o grupo do usuário."

        self.logger.info(f"[check_user_project_permission] Permissão OK: {email} -> {project_id} (Agente: {agent_name})")
        return True, role, None

    async def check_user_project_action_permission(
        self,
        email: str,
        project_id: str,
        action_type: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifica apenas se o usuário pode executar uma ação no projeto (ignora verificação de agente).
        """
        success, role, _, error_msg = await self._resolve_project_access(email, project_id, action_type)
        
        if not success:
            return False, role, error_msg

        self.logger.info(f"[check_user_project_action_permission] Permissão OK: {email} -> {project_id} (Ação: {action_type})")
        return True, role, None

    async def check_user_agent_permission(self, email: str, agent_name: str) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"[check_user_agent_permission] Verificando permissão de agente: '{email}' -> '{agent_name}'.")
        
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, "Usuário não encontrado."
        if not user.active:
            return False, "Usuário inativo."
        
        company_id = getattr(user, "company_id", None)
        if not company_id:
            return False, "Usuário não possui company_id."

        # Tenta Cache
        permissions = self.redis_session_service.get_user_permissions(email, company_id)
        if permissions:
            allowed_agents = permissions.get("allowed_agents", set())
            if agent_name in allowed_agents:
                return True, None
       
            return False, "Usuário não possui permissão para usar este agente."

        # Cache Miss - Constroi e Salva
        permissions_dict = await self._build_complete_permissions(email, company_id)
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        
        allowed_agents = permissions_dict.get("allowed_agents", [])
        if agent_name in allowed_agents:
            return True, None
        
        return False, "Usuário não possui permissão para usar este agente."

    async def check_user_can_create_project(self, email: str, company_id: str) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"[check_user_can_create_project] Verificando permissão de criação para '{email}'.")
        
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            return False, "Usuário não encontrado."
            
        if not hasattr(user, "group_ids") or not user.group_ids:
            return False, "Usuário não pertence a nenhum grupo com permissão de criação."

        can_create = False
        
        for group_id in user.group_ids:
            group = await self.mongo_service.get_group_by_id(group_id)
            if group and hasattr(group, "settings"):
                settings_dict = group.settings if isinstance(group.settings, dict) else group.settings.dict()
                
                if settings_dict.get("can_create_projects") is True:
                    can_create = True
                    self.logger.info(f"[check_user_can_create_project] Permissão concedida pelo grupo '{group.name}'.")
                    break
        
        if can_create:
            return True, None
        else:
            return False, "Seu grupo de usuário não tem permissão para criar novos projetos."
