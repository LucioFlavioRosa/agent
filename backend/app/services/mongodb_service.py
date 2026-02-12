from motor.motor_asyncio import AsyncIOMotorClient
from backend.app.models.permission_models import UserPermission, GroupPermission, ProjectPermission, ProjectMember
from typing import Optional, List
from backend.app.core.config import settings
from backend.app.services.azure_secret_manager import AzureSecretManager
from datetime import datetime
import uuid
import logging
from backend.app.utils import logger_utils

class MongoDBService:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        logger = logging.getLogger("MongoDBService")
        try:
            key_vault_url = getattr(settings, "KEY_VAULT_URL", None)
            if not key_vault_url:
                logger.critical("KEY_VAULT_URL não definido nas configurações.")
                raise EnvironmentError("KEY_VAULT_URL não definido.")
            secret_manager = AzureSecretManager(key_vault_url)
            if uri is None:
                uri = secret_manager.get_secret("mongodb-uri")
            if db_name is None:
                db_name = secret_manager.get_secret("mongodb-database-name")
        except Exception as e:
            logger.critical(f"Erro ao obter segredos do MongoDB do Key Vault: {e}")
            raise
        self.mongo_uri = uri
        self.db_name = db_name
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    async def get_user_by_email(self, email: str) -> Optional[UserPermission]:
        logger_utils.log_request_received("MongoDBService.get_user_by_email", {"email": email})
        try:
            doc = await self.db.users.find_one({"email": email})
            logger_utils.log_service_call("MongoDBService.get_user_by_email", {"email": email, "user_found": bool(doc)})
            if doc:
                company_id = doc.get("company_id")
                user = UserPermission(**doc)
                if not getattr(user, "company_id", None):
                    user.company_id = company_id
                logger_utils.log_response_sent("MongoDBService.get_user_by_email", {"email": email, "success": True})
                return user
            logger_utils.log_response_sent("MongoDBService.get_user_by_email", {"email": email, "success": False})
            return None
        except Exception as e:
            logger_utils.log_response_sent("MongoDBService.get_user_by_email", {"email": email, "success": False, "error": str(e)})
            return None

    async def get_project_by_id(self, project_id: str) -> Optional[ProjectPermission]:
        logger_utils.log_request_received("MongoDBService.get_project_by_id", {"project_id": project_id})
        try:
            doc = await self.db.projects.find_one({"_id": project_id})
            logger_utils.log_service_call("MongoDBService.get_project_by_id", {"project_id": project_id, "project_found": bool(doc)})
            if doc:
                members = [ProjectMember(**m) for m in doc.get("members", [])]
                doc["members"] = members
                logger_utils.log_response_sent("MongoDBService.get_project_by_id", {"project_id": project_id, "success": True})
                return ProjectPermission(**doc)
            logger_utils.log_response_sent("MongoDBService.get_project_by_id", {"project_id": project_id, "success": False})
            return None
        except Exception as e:
            logger_utils.log_response_sent("MongoDBService.get_project_by_id", {"project_id": project_id, "success": False, "error": str(e)})
            return None

    async def get_project_by_normalized_name(self, nome_projeto: str, company_id: str) -> Optional[ProjectPermission]:
        logger_utils.log_request_received("MongoDBService.get_project_by_normalized_name", {"nome_projeto": nome_projeto, "company_id": company_id})
        try:
            nome_projeto_normalizado = nome_projeto.lower().strip()
            doc = await self.db.projects.find_one({"name_normalized": nome_projeto_normalizado, "company_id": company_id})
            logger_utils.log_service_call("MongoDBService.get_project_by_normalized_name", {"nome_projeto_normalizado": nome_projeto_normalizado, "project_found": bool(doc)})
            if doc:
                members = [ProjectMember(**m) for m in doc.get("members", [])]
                doc["members"] = members
                logger_utils.log_response_sent("MongoDBService.get_project_by_normalized_name", {"nome_projeto": nome_projeto, "success": True})
                return ProjectPermission(**doc)
            logger_utils.log_response_sent("MongoDBService.get_project_by_normalized_name", {"nome_projeto": nome_projeto, "success": False})
            return None
        except Exception as e:
            logger_utils.log_response_sent("MongoDBService.get_project_by_normalized_name", {"nome_projeto": nome_projeto, "success": False, "error": str(e)})
            return None

    async def create_project(self, project_data: dict, company_id: str) -> str:
        logger_utils.log_request_received("MongoDBService.create_project", {"project_data": project_data, "company_id": company_id})
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
            logger_utils.log_response_sent("MongoDBService.create_project", {"project_id": project_id, "success": True})
            return project_id
        except Exception as e:
            logger_utils.log_response_sent("MongoDBService.create_project", {"success": False, "error": str(e)})
            raise

    async def add_member_to_project(self, project_id: str, new_member: dict) -> bool:
        logger_utils.log_request_received("MongoDBService.add_member_to_project", {"project_id": project_id, "new_member": new_member})
        try:
            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$addToSet": {"members": new_member}}
            )
            logger_utils.log_service_call("MongoDBService.add_member_to_project", {"project_id": project_id, "modified_count": result.modified_count})
            success = result.modified_count > 0
            logger_utils.log_response_sent("MongoDBService.add_member_to_project", {"project_id": project_id, "success": success})
            return success
        except Exception as e:
            logger_utils.log_response_sent("MongoDBService.add_member_to_project", {"project_id": project_id, "success": False, "error": str(e)})
            return False

    async def update_project_members(self, project_id: str, members: List[dict]) -> bool:
        logger_utils.log_request_received("MongoDBService.update_project_members", {"project_id": project_id, "members_count": len(members)})
        try:
            result = await self.db.projects.update_one(
                {"_id": project_id},
                {"$set": {"members": members}}
            )
            logger_utils.log_service_call("MongoDBService.update_project_members", {"project_id": project_id, "modified_count": result.modified_count})
            success = result.modified_count > 0
            logger_utils.log_response_sent("MongoDBService.update_project_members", {"project_id": project_id, "success": success})
            return success
        except Exception as e:
            logger_utils.log_response_sent("MongoDBService.update_project_members", {"project_id": project_id, "success": False, "error": str(e)})
            return False
