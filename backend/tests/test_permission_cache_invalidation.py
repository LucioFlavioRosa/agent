import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.services.permission_service import PermissionService
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.redis_session_service import RedisSessionService

@pytest.mark.asyncio
async def test_add_member_invalidate_cache():
    mongo = AsyncMock(spec=MongoDBService)
    redis = MagicMock(spec=RedisSessionService)
    permission_service = PermissionService(mongo_service=mongo, redis_session_service=redis)
    # Simula membros antes e depois
    project_id = "proj1"
    company_id = "comp1"
    new_member_email = "new@user.com"
    existing_emails = ["owner@user.com", "editor@user.com"]
    project = MagicMock()
    project.members = [MagicMock(email=e, role="owner") for e in existing_emails]
    project.company_id = company_id
    mongo.get_project_by_id.return_value = project
    # Simula adição
    await mongo.add_member_to_project(project_id, {"email": new_member_email, "role": "editor"})
    # Invalida cache de todos
    for email in existing_emails + [new_member_email]:
        redis.invalidate_user_permissions.assert_any_call(email, company_id)

@pytest.mark.asyncio
async def test_remove_member_invalidate_cache():
    mongo = AsyncMock(spec=MongoDBService)
    redis = MagicMock(spec=RedisSessionService)
    permission_service = PermissionService(mongo_service=mongo, redis_session_service=redis)
    project_id = "proj2"
    company_id = "comp2"
    removed_email = "remove@user.com"
    member_emails = ["owner@user.com", "remove@user.com"]
    project = MagicMock()
    project.members = [MagicMock(email=e, role="owner") for e in member_emails]
    project.company_id = company_id
    mongo.get_project_by_id.return_value = project
    await mongo.remove_member_from_project(project_id, removed_email)
    for email in member_emails:
        redis.invalidate_user_permissions.assert_any_call(email, company_id)

@pytest.mark.asyncio
async def test_modify_group_invalidate_cache():
    mongo = AsyncMock(spec=MongoDBService)
    redis = MagicMock(spec=RedisSessionService)
    group_id = "group1"
    company_id = "comp3"
    group_doc = {"_id": group_id, "company_id": company_id, "members": [{"email": "user1@a.com"}, {"email": "user2@b.com"}]}
    mongo.db.groups.find_one.return_value = group_doc
    # Simula modificação de agentes
    for member in group_doc["members"]:
        redis.invalidate_user_permissions.assert_any_call(member["email"], company_id)

@pytest.mark.asyncio
async def test_modify_user_group_invalidate_cache():
    mongo = AsyncMock(spec=MongoDBService)
    redis = MagicMock(spec=RedisSessionService)
    user_id = "userX"
    company_id = "comp4"
    group_ids = ["groupA", "groupB"]
    user_doc = {"_id": user_id, "email": "userX@domain.com", "company_id": company_id, "group_ids": group_ids}
    mongo.db.users.find_one.return_value = user_doc
    # Simula update de group_ids
    for group_id in group_ids:
        group_doc = {"_id": group_id, "company_id": company_id, "members": [{"email": "userX@domain.com"}, {"email": "other@domain.com"}]}
        mongo.db.groups.find_one.return_value = group_doc
        for member in group_doc["members"]:
            redis.invalidate_user_permissions.assert_any_call(member["email"], company_id)

@pytest.mark.asyncio
async def test_delete_project_invalidate_cache():
    mongo = AsyncMock(spec=MongoDBService)
    redis = MagicMock(spec=RedisSessionService)
    project_id = "projDel"
    company_id = "comp5"
    member_emails = ["owner@domain.com", "editor@domain.com"]
    project = MagicMock()
    project.members = [MagicMock(email=e, role="owner") for e in member_emails]
    project.company_id = company_id
    mongo.get_project_by_id.return_value = project
    await mongo.delete_project(project_id, company_id)
    for email in member_emails:
        redis.invalidate_user_permissions.assert_any_call(email, company_id)
