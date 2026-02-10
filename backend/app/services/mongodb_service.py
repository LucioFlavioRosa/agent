from motor.motor_asyncio import AsyncIOMotorClient
from backend.app.models.mongodb_models import User, Group, Project, ProjectMember
from typing import Optional, List
import os

class MongoDBService:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.mongo_uri = uri or os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.db_name = db_name or os.getenv('MONGODB_DB', 'codeai_ecosystem')
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    async def get_user_by_email(self, email: str) -> Optional[User]:
        doc = await self.db.users.find_one({"email": email})
        if doc:
            return User(**doc)
        return None

    async def get_user_groups(self, user_id: str) -> List[Group]:
        user_doc = await self.db.users.find_one({"_id": user_id})
        if not user_doc or not user_doc.get("group_ids"):
            return []
        group_ids = user_doc["group_ids"]
        cursor = self.db.groups.find({"_id": {"$in": group_ids}})
        groups = [Group(**doc) async for doc in cursor]
        return groups

    async def get_group_allowed_agents(self, group_id: str) -> List[str]:
        group_doc = await self.db.groups.find_one({"_id": group_id})
        if group_doc and group_doc.get("allowed_agents"):
            return group_doc["allowed_agents"]
        return []

    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        doc = await self.db.projects.find_one({"_id": project_id})
        if doc:
            return Project(**doc)
        return None

    async def check_user_project_permission(self, user_id: str, project_id: str) -> Optional[str]:
        project_doc = await self.db.projects.find_one({"_id": project_id})
        if not project_doc or not project_doc.get("members"):
            return None
        for member in project_doc["members"]:
            if member["user_id"] == user_id:
                return member.get("role")
        return None
