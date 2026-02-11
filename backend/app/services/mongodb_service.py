from motor.motor_asyncio import AsyncIOMotorClient
from backend.app.models.permission_models import UserPermission, GroupPermission, ProjectPermission, ProjectMember
from typing import Optional, List
import os
from datetime import datetime

class MongoDBService:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.mongo_uri = uri or os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.db_name = db_name or os.getenv('MONGODB_DB', 'codeai_ecosystem')
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    async def get_user_by_email(self, email: str) -> Optional[UserPermission]:
        doc = await self.db.users.find_one({"email": email})
        if doc:
            return UserPermission(**doc)
        return None

    async def get_user_groups(self, user_id: str) -> List[GroupPermission]:
        user_doc = await self.db.users.find_one({"_id": user_id})
        if not user_doc or not user_doc.get("group_ids"):
            return []
        group_ids = user_doc["group_ids"]
        cursor = self.db.groups.find({"_id": {"$in": group_ids}})
        groups = [GroupPermission(**doc) async for doc in cursor]
        return groups

    async def get_group_allowed_agents(self, group_id: str) -> List[str]:
        group_doc = await self.db.groups.find_one({"_id": group_id})
        if group_doc and group_doc.get("allowed_agents"):
            return group_doc["allowed_agents"]
        return []

    async def get_project_by_id(self, project_id: str) -> Optional[ProjectPermission]:
        doc = await self.db.projects.find_one({"_id": project_id})
        if doc:
            members = [ProjectMember(**m) for m in doc.get("members", [])]
            doc["members"] = members
            return ProjectPermission(**doc)
        return None

    async def check_user_project_permission(self, user_id: str, project_id: str) -> Optional[str]:
        project_doc = await self.db.projects.find_one({"_id": project_id})
        if not project_doc or not project_doc.get("members"):
            return None
        for member in project_doc["members"]:
            if member["user_id"] == user_id:
                return member.get("role")
        return None

    async def get_user_projects_with_access(self, email: str) -> List[dict]:
        user_doc = await self.db.users.find_one({"email": email})
        if not user_doc:
            return []
        user_id = user_doc.get("_id")
        cursor = self.db.projects.find({"members.email": email})
        projects = []
        async for project_doc in cursor:
            project_id = str(project_doc.get("_id"))
            project_name = project_doc.get("name")
            description = project_doc.get("description")
            created_at = project_doc.get("created_at")
            role = None
            for member in project_doc.get("members", []):
                if member.get("email") == email:
                    role = member.get("role")
                    break
            projects.append({
                "project_id": project_id,
                "project_name": project_name,
                "role": role,
                "description": description,
                "created_at": created_at
            })
        return projects

    async def get_projects_where_user_is_owner(self, email: str) -> List[dict]:
        cursor = self.db.projects.find({"members": {"$elemMatch": {"email": email, "role": "owner"}}})
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
        return projects

    async def add_member_to_project(self, project_id: str, new_member: dict) -> bool:
        result = await self.db.projects.update_one(
            {"_id": project_id},
            {"$addToSet": {"members": new_member}}
        )
        return result.modified_count > 0

    async def update_project_members(self, project_id: str, members: List[dict]) -> bool:
        result = await self.db.projects.update_one(
            {"_id": project_id},
            {"$set": {"members": members}}
        )
        return result.modified_count > 0

    async def create_project(self, project_id: str, nome_projeto: str, company_id: str, email: str, user_id: str) -> bool:
        now = datetime.utcnow()
        project_doc = {
            "_id": project_id,
            "name": nome_projeto,
            "description": None,
            "company_id": company_id,
            "blob_path": None,
            "members": [
                {
                    "user_id": user_id,
                    "email": email,
                    "role": "owner",
                    "added_at": now.isoformat()
                }
            ],
            "created_at": now,
            "updated_at": now
        }
        result = await self.db.projects.insert_one(project_doc)
        return result.acknowledged
