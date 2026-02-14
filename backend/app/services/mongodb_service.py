from motor.motor_asyncio import AsyncIOMotorClient
from backend.app.models.permission_models import UserPermission, GroupPermission, ProjectPermission, ProjectMember
from typing import Optional, List
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager
from datetime import datetime
import uuid
import logging

class MongoDBService:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.logger = logging.getLogger("MongoDBService")
        # Extração dos segredos do Key Vault se não fornecidos
        if uri is None or db_name is None:
            try:
                key_vault_url = getattr(settings, "KEY_VAULT_URL", None)
                if not key_vault_url:
                    self.logger.critical("KEY_VAULT_URL não definido nas configurações.")
                    raise EnvironmentError("KEY_VAULT_URL não definido.")
                secret_manager = AzureSecretManager(key_vault_url)
                if uri is None:
                    uri = secret_manager.get_secret("azure-mongodb-connection-string")
                if db_name is None:
                    db_name = secret_manager.get_secret("azure-mongodb-database-name")
            except Exception as e:
                self.logger.critical(f"Erro ao obter segredos do MongoDB do Key Vault: {e}")
                raise
        self.mongo_uri = uri
        self.db_name = db_name
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    async def get_user_by_email(self, email: str) -> Optional[UserPermission]:
        self.logger.info(f"[get_user_by_email] Iniciando busca de usuário por email: '{email}'")
        try:
            doc = await self.db.users.find_one({"email": email})
            self.logger.info(f"[get_user_by_email] Resultado da consulta: {doc}")
            if doc:
                company_id = doc.get("company_id")
                user = UserPermission(**doc)
                if not getattr(user, "company_id", None):
                    user.company_id = company_id
                self.logger.info(f"[get_user_by_email] Usuário encontrado e instanciado: {user}")
                return user
            self.logger.warning(f"[get_user_by_email] Usuário '{email}' não encontrado.")
            return None
        except Exception as e:
            self.logger.error(f"[get_user_by_email] Erro ao buscar usuário '{email}': {e}")
            return None

    async def get_user_groups(self, user_id: str) -> List[GroupPermission]:
        self.logger.info(f"[get_user_groups] Iniciando busca de grupos para user_id: '{user_id}'")
        try:
            user_doc = await self.db.users.find_one({"_id": user_id})
            if not user_doc or not user_doc.get("group_ids"):
                self.logger.warning(f"[get_user_groups] Usuário '{user_id}' não possui grupos.")
                return []
            group_ids = user_doc["group_ids"]
            cursor = self.db.groups.find({"_id": {"$in": group_ids}})
            groups = [GroupPermission(**doc) async for doc in cursor]
            self.logger.info(f"[get_user_groups] Grupos encontrados: {[g.name for g in groups]}")
            return groups
        except Exception as e:
            self.logger.error(f"[get_user_groups] Erro ao buscar grupos para user_id '{user_id}': {e}")
            return []

    async def get_group_allowed_agents(self, group_id: str) -> List[str]:
        self.logger.info(f"[get_group_allowed_agents] Iniciando busca de agentes permitidos para group_id: '{group_id}'")
        try:
            group_doc = await self.db.groups.find_one({"_id": group_id})
            if group_doc and group_doc.get("allowed_agents"):
                self.logger.info(f"[get_group_allowed_agents] Agentes permitidos encontrados: {group_doc['allowed_agents']}")
                return group_doc["allowed_agents"]
            self.logger.warning(f"[get_group_allowed_agents] Grupo '{group_id}' não possui agentes permitidos.")
            return []
        except Exception as e:
            self.logger.error(f"[get_group_allowed_agents] Erro ao buscar agentes permitidos para group_id '{group_id}': {e}")
            return []

    async def get_group_by_id(self, group_id: str) -> Optional[GroupPermission]:
        self.logger.info(f"[get_group_by_id] Iniciando busca de grupo por id: '{group_id}'")
        try:
            doc = await self.db.groups.find_one({"_id": group_id})
            self.logger.info(f"[get_group_by_id] Resultado da consulta: {doc}")
            if doc:
                group = GroupPermission(**doc)
                self.logger.info(f"[get_group_by_id] Grupo encontrado e instanciado: {group}")
                return group
            self.logger.warning(f"[get_group_by_id] Grupo '{group_id}' não encontrado.")
            return None
        except Exception as e:
            self.logger.error(f"[get_group_by_id] Erro ao buscar grupo '{group_id}': {e}")
            return None

    async def list_groups_by_company(self, company_id: str) -> List[GroupPermission]:
        self.logger.info(f"[list_groups_by_company] Iniciando busca de grupos para company_id: '{company_id}'")
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.warning(f"[list_groups_by_company] company_id inválido ou vazio: '{company_id}'")
            return []
        try:
            cursor = self.db.groups.find({"company_id": company_id})
            groups = [GroupPermission(**doc) async for doc in cursor]
            self.logger.info(f"[list_groups_by_company] Grupos encontrados: {[g.name for g in groups]}")
            return groups
        except Exception as e:
            self.logger.error(f"[list_groups_by_company] Erro ao buscar grupos para company_id '{company_id}': {e}")
            return []

    async def get_project_by_id(self, project_id: str) -> Optional[ProjectPermission]:
        self.logger.info(f"[get_project_by_id] Iniciando busca de projeto por id: '{project_id}'")
        try:
            doc = await self.db.projects.find_one({"_id": project_id})
            self.logger.info(f"[get_project_by_id] Resultado da consulta: {doc}")
            if doc:
                members = [ProjectMember(**m) for m in doc.get("members", [])]
                doc["members"] = members
                project = ProjectPermission(**doc)
                self.logger.info(f"[get_project_by_id] Projeto encontrado e instanciado: {project}")
                return project
            self.logger.warning(f"[get_project_by_id] Projeto '{project_id}' não encontrado.")
            return None
        except Exception as e:
            self.logger.error(f"[get_project_by_id] Erro ao buscar projeto '{project_id}': {e}")
            return None

    async def check_user_project_permission(self, user_id: str, project_id: str) -> Optional[str]:
        self.logger.info(f"[check_user_project_permission] Iniciando verificação de permissão para user_id: '{user_id}', project_id: '{project_id}'")
        try:
            project_doc = await self.db.projects.find_one({"_id": project_id})
            if not project_doc or not project_doc.get("members"):
                self.logger.warning(f"[check_user_project_permission] Projeto '{project_id}' não encontrado ou sem membros.")
                return None
            for member in project_doc["members"]:
                if member["user_id"] == user_id:
                    self.logger.info(f"[check_user_project_permission] Role encontrado para user_id '{user_id}': {member.get('role')}")
                    return member.get("role")
            self.logger.warning(f"[check_user_project_permission] user_id '{user_id}' não possui permissão no projeto '{project_id}'.")
            return None
        except Exception as e:
            self.logger.error(f"[check_user_project_permission] Erro ao verificar permissão para user_id '{user_id}' no projeto '{project_id}': {e}")
            return None

    async def get_user_projects_with_access(self, email: str) -> List[dict]:
        self.logger.info(f"[get_user_projects_with_access] Iniciando busca de projetos com acesso para email: '{email}'")
        try:
            user_doc = await self.db.users.find_one({"email": email})
            if not user_doc:
                self.logger.warning(f"[get_user_projects_with_access] Usuário '{email}' não encontrado.")
                return []
            user_id = user_doc.get("_id")
            cursor = self.db.projects.find({"members.email": email})
            async def _build_project_dict(project_doc, email):
                project_id = str(project_doc.get("_id"))
                project_name = project_doc.get("name")
                description = project_doc.get("description")
                created_at = project_doc.get("created_at")
                role = next((member.get("role") for member in project_doc.get("members", []) if member.get("email") == email), None)
                return {
                    "project_id": project_id,
                    "project_name": project_name,
                    "role": role,
                    "description": description,
                    "created_at": created_at
                }
            projects = [await _build_project_dict(project_doc, email) async for project_doc in cursor]
            self.logger.info(f"[get_user_projects_with_access] Projetos encontrados: {projects}")
            return projects
        except Exception as e:
            self.logger.error(f"[get_user_projects_with_access] Erro ao buscar projetos para email '{email}': {e}")
            return []

    async def get_projects_where_user_is_owner(self, email: str, company_id: str) -> List[dict]:
        self.logger.info(f"[get_projects_where_user_is_owner] Iniciando busca de projetos onde '{email}' é owner, company_id: '{company_id}'")
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.error(f"[get_projects_where_user_is_owner] company_id inválido ou vazio: '{company_id}'")
            raise ValueError("company_id é obrigatório e não pode ser vazio.")
        try:
            cursor = self.db.projects.find({
                "members": {"$elemMatch": {"email": email, "role": "owner"}},
                "company_id": company_id
            })
            projects = []
            async for project_doc in cursor:
                project_id = str(project_doc.get("_id"))
                name = project_doc.get("name")
                description = project_doc.get("description")
                members = project_doc.get("members", [])
                projects.append({
                    "project_id": project_id,
                    "name": name,
                    "description": description,
                    "members": members
                })
            self.logger.info(f"[get_projects_where_user_is_owner] Projetos encontrados: {projects}")
            return projects
        except Exception as e:
            self.logger.error(f"[get_projects_where_user_is_owner] Erro ao buscar projetos para owner '{email}': {e}")
            return []

    async def add_member_to_project(self, project_id: str, new_member: dict) -> bool:
        self.logger.info(f"[add_member_to_project] Iniciando adição de membro ao projeto '{project_id}'. Dados do membro: {new_member}")
        try:
            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$addToSet": {"members": new_member}}
            )
            self.logger.info(f"[add_member_to_project] Resultado da operação: modified_count={result.modified_count}")
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"[add_member_to_project] Erro ao adicionar membro ao projeto '{project_id}': {e}")
            return False

    async def update_project_members(self, project_id: str, members: List[dict]) -> bool:
        self.logger.info(f"[update_project_members] Iniciando atualização de membros do projeto '{project_id}'. Lista de membros: {members}")
        try:
            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$set": {"members": members}}
            )
            self.logger.info(f"[update_project_members] Resultado da operação: modified_count={result.modified_count}")
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"[update_project_members] Erro ao atualizar membros do projeto '{project_id}': {e}")
            return False

    async def get_project_by_normalized_name(self, nome_projeto: str, company_id: str) -> Optional[ProjectPermission]:
        self.logger.info(f"[get_project_by_normalized_name] Iniciando busca de projeto por nome normalizado: '{nome_projeto}', company_id: '{company_id}'")
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.error(f"[get_project_by_normalized_name] company_id inválido ou vazio: '{company_id}'")
            raise ValueError("company_id é obrigatório e não pode ser vazio.")
        nome_projeto_normalizado = nome_projeto.lower().strip()
        try:
            doc = await self.db.projects.find_one({"name_normalized": nome_projeto_normalizado, "company_id": company_id})
            self.logger.info(f"[get_project_by_normalized_name] Resultado da consulta: {doc}")
            if doc:
                members = [ProjectMember(**m) for m in doc.get("members", [])]
                doc["members"] = members
                project = ProjectPermission(**doc)
                self.logger.info(f"[get_project_by_normalized_name] Projeto encontrado e instanciado: {project}")
                return project
            self.logger.warning(f"[get_project_by_normalized_name] Projeto '{nome_projeto_normalizado}' não encontrado.")
            return None
        except Exception as e:
            self.logger.error(f"[get_project_by_normalized_name] Erro ao buscar projeto '{nome_projeto_normalizado}': {e}")
            return None

    async def create_project(self, project_data: dict, company_id: str) -> str:
        self.logger.info(f"[create_project] Iniciando criação de projeto. Dados: {project_data}, company_id: '{company_id}'")
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.error(f"[create_project] company_id inválido ou vazio: '{company_id}'")
            raise ValueError("company_id é obrigatório e não pode ser vazio.")
        try:
            project_id = str(uuid.uuid4())
            nome_projeto = project_data.get("name")
            name_normalized = nome_projeto.lower().strip() if nome_projeto else ""
            description = project_data.get("description")
            members = project_data.get("members", [])
            now = datetime.utcnow()
            doc = {
                "_id": project_id,
                "name": nome_projeto,
                "name_normalized": name_normalized,
                "description": description,
                "company_id": company_id,
                "members": members,
                "created_at": now,
                "updated_at": now
            }
            await self.db.projects.insert_one(doc)
            self.logger.info(f"[create_project] Projeto criado com sucesso: {doc}")
            return project_id
        except Exception as e:
            self.logger.error(f"[create_project] Erro ao criar projeto: {e}")
            raise

    async def delete_project(self, project_id: str, company_id: str) -> bool:
        self.logger.info(f"[delete_project] Iniciando exclusão do projeto. project_id: '{project_id}', company_id: '{company_id}'")
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            self.logger.error(f"[delete_project] project_id inválido ou vazio: '{project_id}'")
            return False
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.error(f"[delete_project] company_id inválido ou vazio: '{company_id}'")
            return False
        try:
            result = await self.db.projects.delete_one({"_id": project_id, "company_id": company_id})
            self.logger.info(f"[delete_project] Resultado da operação: deleted_count={result.deleted_count}")
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"[delete_project] Erro ao excluir projeto '{project_id}': {e}")
            return False
