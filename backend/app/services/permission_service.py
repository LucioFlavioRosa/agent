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
            "project_permissions": project_permissions,
            "email": email,
            "company_id": company_id,
            "cached_at": __import__('datetime').datetime.utcnow().isoformat()
        }

    async def get_user_allowed_agents(self, email: str, company_id: str) -> List[str]:
        """
        Retorna a lista de agentes que o usuário pode acessar, usando cache Redis e fallback MongoDB.
        """
        self.logger.info(f"[get_user_allowed_agents] Consultando agentes permitidos para email='{email}', company_id='{company_id}'")
        # 1. Busca no Redis
        permissions = self.redis_session_service.get_user_permissions(email, company_id)
        if permissions and 'allowed_agents' in permissions:
            self.logger.info(f"[get_user_allowed_agents] Cache hit no Redis para {email}:{company_id}")
            return permissions['allowed_agents']
        self.logger.info(f"[get_user_allowed_agents] Cache miss. Buscando no MongoDB.")
        # 2. Busca usuário no MongoDB
        user = await self.mongo_service.get_user_by_email(email)
        if not user:
            self.logger.warning(f"[get_user_allowed_agents] Usuário '{email}' não encontrado no MongoDB.")
            return []
        user_company_id = getattr(user, "company_id", None)
        if not user_company_id or user_company_id != company_id:
            self.logger.warning(f"[get_user_allowed_agents] company_id inválido ou não corresponde ao usuário.")
            return []
        group_ids = getattr(user, "group_ids", [])
        allowed_agents_set = set()
        for group_id in group_ids:
            group = await self.mongo_service.get_group_by_id(group_id)
            if group and hasattr(group, "allowed_agents"):
                allowed_agents_set.update(group.allowed_agents)
        allowed_agents = list(allowed_agents_set)
        # 3. Reconstrói permissões completas e salva no Redis
        permissions_dict = await self._build_complete_permissions(email, company_id)
        self.redis_session_service.store_user_permissions(email, company_id, permissions_dict)
        self.logger.info(f"[get_user_allowed_agents] Permissões cacheadas no Redis para {email}:{company_id}")
        return allowed_agents

    # ... (restante do código original permanece inalterado)
