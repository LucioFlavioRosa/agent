import pytest
from httpx import AsyncClient
from fastapi import status
from backend.app.main import app
import motor.motor_asyncio
import asyncio

@pytest.fixture(scope="module")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="module")
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="function")
async def setup_projects_and_users():
    # Setup MongoDB test data
    mongo_service = app.state.mongo_service
    db = mongo_service.db
    # Clean collections
    await db.users.delete_many({})
    await db.projects.delete_many({})
    # Create users
    owner = {
        "_id": "user-owner-id",
        "email": "owner@test.com",
        "name": "Owner User",
        "company_id": "company-test-id",
        "active": True,
        "group_ids": ["group-devs-id"]
    }
    editor = {
        "_id": "user-editor-id",
        "email": "editor@test.com",
        "name": "Editor User",
        "company_id": "company-test-id",
        "active": True,
        "group_ids": ["group-devs-id"]
    }
    viewer = {
        "_id": "user-viewer-id",
        "email": "viewer@test.com",
        "name": "Viewer User",
        "company_id": "company-test-id",
        "active": True,
        "group_ids": ["group-devs-id"]
    }
    await db.users.insert_many([owner, editor, viewer])
    # Create project
    project_id = "project-test-id"
    project = {
        "_id": project_id,
        "name": "Projeto Teste",
        "company_id": "company-test-id",
        "members": [
            {"user_id": "user-owner-id", "email": "owner@test.com", "role": "owner", "added_at": None},
            {"user_id": "user-editor-id", "email": "editor@test.com", "role": "editor", "added_at": None},
            {"user_id": "user-viewer-id", "email": "viewer@test.com", "role": "viewer", "added_at": None}
        ],
        "created_at": None,
        "updated_at": None
    }
    await db.projects.insert_one(project)
    yield {
        "project_id": project_id,
        "owner_email": "owner@test.com",
        "editor_email": "editor@test.com",
        "viewer_email": "viewer@test.com"
    }
    # Clean up after test
    await db.users.delete_many({})
    await db.projects.delete_many({})

@pytest.mark.anyio
async def test_owner_can_delete_project(test_client, setup_projects_and_users):
    project_id = setup_projects_and_users["project_id"]
    owner_email = setup_projects_and_users["owner_email"]
    # Simulate delete by owner
    response = await test_client.delete(f"/projects/{project_id}", params={"email": owner_email})
    assert response.status_code == status.HTTP_200_OK or response.status_code == status.HTTP_204_NO_CONTENT
    # Project should be removed
    mongo_service = app.state.mongo_service
    project = await mongo_service.db.projects.find_one({"_id": project_id})
    assert project is None

@pytest.mark.anyio
async def test_editor_cannot_delete_project(test_client, setup_projects_and_users):
    project_id = setup_projects_and_users["project_id"]
    editor_email = setup_projects_and_users["editor_email"]
    # Simulate delete by editor
    response = await test_client.delete(f"/projects/{project_id}", params={"email": editor_email})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "não permitida" in response.text or "forbidden" in response.text.lower()

@pytest.mark.anyio
async def test_viewer_cannot_delete_project(test_client, setup_projects_and_users):
    project_id = setup_projects_and_users["project_id"]
    viewer_email = setup_projects_and_users["viewer_email"]
    # Simulate delete by viewer
    response = await test_client.delete(f"/projects/{project_id}", params={"email": viewer_email})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "não permitida" in response.text or "forbidden" in response.text.lower()

@pytest.mark.anyio
async def test_delete_nonexistent_project_returns_404(test_client):
    project_id = "project-nonexistent-id"
    owner_email = "owner@test.com"
    response = await test_client.delete(f"/projects/{project_id}", params={"email": owner_email})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.text or "not found" in response.text.lower()

@pytest.mark.anyio
async def test_post_members_invalid_role_returns_400(test_client, setup_projects_and_users):
    project_id = setup_projects_and_users["project_id"]
    owner_email = setup_projects_and_users["owner_email"]
    payload = {
        "requester_email": owner_email,
        "project_id": project_id,
        "new_member_email": "newuser@test.com",
        "role": "invalid_role"
    }
    response = await test_client.post(f"/projects/{project_id}/members", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_403_FORBIDDEN
    assert "Role inválida" in response.text or "invalid role" in response.text.lower()

@pytest.mark.anyio
async def test_put_members_invalid_role_returns_400(test_client, setup_projects_and_users):
    project_id = setup_projects_and_users["project_id"]
    owner_email = setup_projects_and_users["owner_email"]
    members = [
        {"user_id": "user-owner-id", "email": "owner@test.com", "role": "owner", "added_at": None},
        {"user_id": "user-editor-id", "email": "editor@test.com", "role": "invalid_role", "added_at": None}
    ]
    payload = {
        "requester_email": owner_email,
        "project_id": project_id,
        "members": members
    }
    response = await test_client.put(f"/projects/{project_id}/members", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_403_FORBIDDEN
    assert "Role inválida" in response.text or "invalid role" in response.text.lower()

@pytest.mark.anyio
async def test_put_members_must_have_at_least_one_owner(test_client, setup_projects_and_users):
    project_id = setup_projects_and_users["project_id"]
    owner_email = setup_projects_and_users["owner_email"]
    # Remove owner from members
    members = [
        {"user_id": "user-editor-id", "email": "editor@test.com", "role": "editor", "added_at": None},
        {"user_id": "user-viewer-id", "email": "viewer@test.com", "role": "viewer", "added_at": None}
    ]
    payload = {
        "requester_email": owner_email,
        "project_id": project_id,
        "members": members
    }
    response = await test_client.put(f"/projects/{project_id}/members", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_403_FORBIDDEN
    assert "owner" in response.text.lower() or "deve haver pelo menos um owner" in response.text.lower()
