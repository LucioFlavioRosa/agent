from motor.motor_asyncio import AsyncIOMotorClient
from backend.app.models.permission_models import UserPermission, GroupPermission, ProjectPermission, ProjectMember
from pymongo.errors import DuplicateKeyError
from typing import Optional, List
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager
from backend.app.services.redis_session_service import RedisSessionService
from datetime import datetime
import uuid
import logging

from backend.app.utils.string_utils import normalize_string_general

class MongoDBService:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.logger = logging.getLogger("MongoDBService")
        self.mongo_uri = uri or settings.AZURE_MONGODB_CONNECTION_STRING
        self.db_name = db_name or settings.AZURE_MONGODB_DATABASE_NAME

        if not self.mongo_uri or not self.db_name:
             self.logger.critical("MongoDB URI ou DB Name não definidos.")
             raise ValueError("Configuração do MongoDB ausente.")

        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    async def create_indexes(self):
        """Cria índices únicos para garantir integridade dos dados."""
        try:
            await self.db.projects.create_index(
                [("name_normalized", 1), ("company_id", 1)],
                unique=True,
                name="unique_project_name_per_company"
            )
            self.logger.info("[Indexes] Índice único de projetos criado/verificado com sucesso.")
        except Exception as e:
            self.logger.error(f"[Indexes] Erro ao criar índices: {e}")

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
                assigned_group_id = project_doc.get("assigned_group_id") # 🚀 ADICIONADO AQUI
                role = next((member.get("role") for member in project_doc.get("members", []) if member.get("email") == email), None)
                return {
                    "project_id": project_id,
                    "project_name": project_name,
                    "assigned_group_id": assigned_group_id, # 🚀 ADICIONADO AQUI
                    "role": role,
                    "description": description,
                    "created_at": created_at,
                    "latest_reports": project_doc.get("latest_reports", {})
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
        self.logger.info(f"[add_member_to_project] Adicionando membro '{new_member.get('email')}' ao projeto '{project_id}'.")
        try:
            project_doc = await self.db.projects.find_one({"_id": project_id})
            if not project_doc:
                return False
            
            company_id = project_doc.get("company_id")

            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$addToSet": {"members": new_member}}
            )
            
            if result.modified_count > 0:
                email_novo_membro = new_member.get("email")
                if email_novo_membro:
                    await RedisSessionService().invalidate_user_permissions(email_novo_membro, company_id)
                    self.logger.info(f"[Cache] Invalidado apenas para o novo membro: {email_novo_membro}")
            
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"[add_member_to_project] Erro: {e}")
            return False

    async def update_project_members(self, project_id: str, members: List[dict]) -> bool:
        self.logger.info(f"[update_project_members] Iniciando atualização de membros do projeto '{project_id}'.")
        
        try:
            current_project_doc = await self.db.projects.find_one({"_id": project_id})
            
            if not current_project_doc:
                self.logger.warning(f"[update_project_members] Projeto {project_id} não encontrado.")
                return False

            company_id = current_project_doc.get("company_id")
            old_members_list = current_project_doc.get("members", [])

            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$set": {"members": members}}
            )
            
            self.logger.info(f"[update_project_members] Resultado da operação: modified_count={result.modified_count}")

            if result.modified_count > 0:
                redis_service = RedisSessionService()
                
                old_map = {m.get("email"): m.get("role") for m in old_members_list if m.get("email")}
                new_map = {m.get("email"): m.get("role") for m in members if m.get("email")}
                
                all_emails = set(old_map.keys()) | set(new_map.keys())
                
                invalidated_count = 0
                for email in all_emails:
                    old_role = old_map.get(email)
                    new_role = new_map.get(email)

                    if old_role != new_role:
                        await redis_service.invalidate_user_permissions(email, company_id)
                        invalidated_count += 1
                
                self.logger.info(f"[Cache] Cache invalidado para {invalidated_count} usuários que tiveram alterações de permissão.")

            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"[update_project_members] Erro ao atualizar membros do projeto '{project_id}': {e}")
            return False

    async def remove_member_from_project(self, project_id: str, target_email: str) -> bool:
        self.logger.info(f"[remove_member_from_project] Removendo '{target_email}' do projeto '{project_id}'.")
        try:
            project_doc = await self.db.projects.find_one({"_id": project_id})
            if not project_doc:
                return False
                
            company_id = project_doc.get("company_id")

            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$pull": {"members": {"email": target_email}}}
            )

            if result.modified_count > 0:
                await RedisSessionService().invalidate_user_permissions(target_email, company_id)
                self.logger.info(f"[Cache] Invalidado apenas para o membro removido: {target_email}")
            
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"[remove_member_from_project] Erro: {e}")
            return False

    async def get_project_by_normalized_name(self, nome_projeto_normalizado: str, company_id: str) -> Optional[ProjectPermission]:
        self.logger.info(f"[get_project_by_normalized_name] Iniciando busca de projeto por nome normalizado: '{nome_projeto_normalizado}', company_id: '{company_id}'")
        
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.error(f"[get_project_by_normalized_name] company_id inválido ou vazio: '{company_id}'")
            raise ValueError("company_id é obrigatório e não pode ser vazio.") 
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

    async def create_project(self, project_data: dict, company_id: str) -> Optional[str]:
        self.logger.info(f"[create_project] Iniciando criação de projeto. Dados: {project_data}, company_id: '{company_id}'")
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            self.logger.error(f"[create_project] company_id inválido ou vazio: '{company_id}'")
            raise ValueError("company_id é obrigatório e não pode ser vazio.")
        try:
            project_id = project_data.get("_id") or str(uuid.uuid4())
            nome_projeto = project_data.get("name")
            name_normalized = normalize_string_general(nome_projeto)
            description = project_data.get("description")
            members = project_data.get("members", [])
            assigned_group_id = project_data.get("assigned_group_id") # 🚀 ADICIONADO AQUI
            now = datetime.utcnow()
            doc = {
                "_id": project_id,
                "name": nome_projeto,
                "name_normalized": name_normalized,
                "description": description,
                "company_id": company_id,
                "assigned_group_id": assigned_group_id, # 🚀 ADICIONADO AQUI
                "members": members,
                "created_at": now,
                "updated_at": now
            }
            await self.db.projects.insert_one(doc)
            self.logger.info(f"[create_project] Projeto criado com sucesso: {project_id}")
            # Cache invalidation: todos membros do projeto
            affected_emails = [m.get("email") for m in members if m.get("email")]
            for email in set(affected_emails):
                await RedisSessionService().invalidate_user_permissions(email, company_id)
            return project_id
        except DuplicateKeyError:
            self.logger.warning(f"[create_project] Tentativa de criar projeto duplicado: '{name_normalized}' para a empresa '{company_id}'")
            return None
        except Exception as e:
            self.logger.error(f"[create_project] Erro inesperado ao criar projeto: {e}")
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
            project_doc = await self.db.projects.find_one({"_id": project_id, "company_id": company_id})
            result = await self.db.projects.delete_one({"_id": project_id, "company_id": company_id})
            self.logger.info(f"[delete_project] Resultado da operação: deleted_count={result.deleted_count}")
            # Cache invalidation: todos membros do projeto
            if result.deleted_count > 0 and project_doc:
                affected_emails = [m.get("email") for m in project_doc.get("members", []) if m.get("email")]
                for email in set(affected_emails):
                    await RedisSessionService().invalidate_user_permissions(email, company_id)
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"[delete_project] Erro ao excluir projeto '{project_id}': {e}")
            return False

    async def create_group(self, group_data: dict) -> Optional[str]:
        self.logger.info(f"[create_group] Iniciando criação de grupo. Dados: {group_data}")
        try:
            group_id = group_data.get("_id") or str(uuid.uuid4())
            group_data["_id"] = group_id
            await self.db.groups.insert_one(group_data)
            self.logger.info(f"[create_group] Grupo criado com sucesso: {group_id}")
            # Cache invalidation: todos usuários do grupo
            users_cursor = self.db.users.find({"group_ids": group_id})
            async for user_doc in users_cursor:
                email = user_doc.get("email")
                company_id = user_doc.get("company_id")
                if email and company_id:
                    await RedisSessionService().invalidate_user_permissions(email, company_id)
            return group_id
        except Exception as e:
            self.logger.error(f"[create_group] Erro ao criar grupo: {e}")
            return None

    async def update_group(self, group_id: str, group_data: dict) -> bool:
        self.logger.info(f"[update_group] Iniciando atualização de grupo '{group_id}'. Dados: {group_data}")
        try:
            result = await self.db.groups.update_one({"_id": group_id}, {"$set": group_data})
            self.logger.info(f"[update_group] Resultado da operação: modified_count={result.modified_count}")
            # Cache invalidation: todos usuários do grupo
            if result.modified_count > 0:
                users_cursor = self.db.users.find({"group_ids": group_id})
                async for user_doc in users_cursor:
                    email = user_doc.get("email")
                    company_id = user_doc.get("company_id")
                    if email and company_id:
                        await RedisSessionService().invalidate_user_permissions(email, company_id)
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"[update_group] Erro ao atualizar grupo '{group_id}': {e}")
            return False

    async def delete_group(self, group_id: str) -> bool:
        self.logger.info(f"[delete_group] Iniciando exclusão de grupo '{group_id}'.")
        try:
            group_doc = await self.db.groups.find_one({"_id": group_id})
            result = await self.db.groups.delete_one({"_id": group_id})
            self.logger.info(f"[delete_group] Resultado da operação: deleted_count={result.deleted_count}")
            # Cache invalidation: todos usuários do grupo
            if result.deleted_count > 0:
                users_cursor = self.db.users.find({"group_ids": group_id})
                async for user_doc in users_cursor:
                    email = user_doc.get("email")
                    company_id = user_doc.get("company_id")
                    if email and company_id:
                        await RedisSessionService().invalidate_user_permissions(email, company_id)
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"[delete_group] Erro ao excluir grupo '{group_id}': {e}")
            return False

    async def get_report_context_tree(self, project_id: str, job_id: str, category: str) -> dict:
        """
        Dada uma categoria e um job_id específico, reconstrói o contexto 
        olhando para o passado (o que gerou ele) e para o futuro (o que ele gerou).
        """
        # 1. Busca o relatório alvo (ex: Features V2)
        target_report = await self.db.project_reports_history.find_one({"job_id": job_id})
        if not target_report:
            return None

        context_used = target_report.get("context_used", {})
        
        # Estrutura de resposta
        tree = {
            "epics": None,
            "features": None,
            "timeline": None,
            "risks": None
        }
        
        # Coloca o alvo no lugar certo
        tree[category] = target_report

        # 2. OLHANDO PARA O PASSADO (Ancestrais)
        # Se eu sou Feature, preciso do Épico exato que me gerou
        if category in ["features", "timeline", "risks"] and context_used.get("epics_job_id"):
            tree["epics"] = await self.db.project_reports_history.find_one({"job_id": context_used["epics_job_id"]})
            
        if category in ["timeline", "risks"] and context_used.get("features_job_id"):
             tree["features"] = await self.db.project_reports_history.find_one({"job_id": context_used["features_job_id"]})
             
        if category == "risks" and context_used.get("timeline_job_id"):
             tree["timeline"] = await self.db.project_reports_history.find_one({"job_id": context_used["timeline_job_id"]})

        # 3. OLHANDO PARA O FUTURO (Descendentes Mais Recentes)
        # Se eu sou Feature, quais Timelines e Riscos mais novos foram gerados a partir de mim?
        if category == "epics":
            # Busca a feature mais recente que usou este épico específico
            tree["features"] = await self._get_latest_descendant("features", "epics_job_id", job_id)
            
        if category in ["epics", "features"]:
            # Busca a timeline mais recente que usou esta feature (ou épico se não houver feature)
            child_job = tree["features"]["job_id"] if tree["features"] else job_id
            child_field = "features_job_id" if tree["features"] else "epics_job_id"
            tree["timeline"] = await self._get_latest_descendant("timeline", child_field, child_job)
            
        if category in ["epics", "features", "timeline"]:
            child_job = tree["timeline"]["job_id"] if tree["timeline"] else (tree["features"]["job_id"] if tree["features"] else job_id)
            child_field = "timeline_job_id" if tree["timeline"] else ("features_job_id" if tree["features"] else "epics_job_id")
            tree["risks"] = await self._get_latest_descendant("risks", child_field, child_job)

        return tree

    # Helper interno (CORRIGIDO 🚀)
    async def _get_latest_descendant(self, target_category: str, dependency_field: str, dependency_job_id: str):
        cursor = self.db.project_reports_history.find({
            "report_category": target_category,
            f"context_used.{dependency_field}": dependency_job_id,
            "status": "done"
        }).sort("version", -1).limit(1)
        
        docs = await cursor.to_list(length=1)
        return docs[0] if docs else None

    async def update_project_latest_reports(self, project_id: str, new_reports: dict):
        """
        Atualiza campos específicos dentro do dicionário 'latest_reports' de um projeto,
        sem apagar os outros campos que já estavam lá.
        """
        self.logger.info(f"[update_project_latest_reports] Atualizando linhagem do projeto: {project_id}")
        try:
            # Cria a estrutura de "set" para o Mongo no formato: {"latest_reports.epics": "123", ...}
            update_query = {
                f"latest_reports.{key}": value 
                for key, value in new_reports.items()
            }
            
            # Atualiza também a data de alteração
            update_query["updated_at"] = datetime.utcnow()
            
            await self.db.projects.update_one(
                {"_id": project_id},
                {"$set": update_query}
            )
            return True
        except Exception as e:
            self.logger.error(f"[update_project_latest_reports] Erro ao atualizar latest_reports: {e}")
            return False
