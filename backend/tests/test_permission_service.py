import pytest
from backend.app.services.permission_service import PermissionService
import asyncio

@pytest.mark.asyncio
class TestValidateProjectActionByRole:
    @pytest.mark.parametrize("role, action_type, expected_allowed, expected_message", [
        ("owner", "add_member", True, None),
        ("owner", "delete", True, None),
        ("owner", "edit", True, None),
        ("owner", "view", True, None),
        ("editor", "edit", True, None),
        ("editor", "view", True, None),
        ("editor", "add_member", False, "Ação 'add_member' não permitida para role 'editor'."),
        ("editor", "delete", False, "Ação 'delete' não permitida para role 'editor'."),
        ("viewer", "view", True, None),
        ("viewer", "edit", False, "Ação 'edit' não permitida para role 'viewer'."),
        ("viewer", "add_member", False, "Ação 'add_member' não permitida para role 'viewer'."),
        ("viewer", "delete", False, "Ação 'delete' não permitida para role 'viewer'.")
    ])
    async def test_validate_project_action_by_role(self, role, action_type, expected_allowed, expected_message):
        permission_service = PermissionService()
        allowed, message = permission_service.validate_project_action_by_role(role, action_type)
        assert allowed == expected_allowed
        if not allowed:
            assert message == expected_message
        else:
            assert message is None

    def test_validate_project_action_by_role_invalid_role(self):
        permission_service = PermissionService()
        allowed, message = permission_service.validate_project_action_by_role("invalid_role", "view")
        assert allowed is False
        assert message == "Role 'invalid_role' não reconhecida."

    def test_validate_project_action_by_role_invalid_action(self):
        permission_service = PermissionService()
        allowed, message = permission_service.validate_project_action_by_role("owner", "invalid_action")
        assert allowed is False
        assert message == "Ação 'invalid_action' não reconhecida."

@pytest.mark.asyncio
class TestCheckUserProjectActionPermissionIntegration:
    @pytest.mark.parametrize("role, action_type, expected_allowed", [
        ("owner", "add_member", True),
        ("owner", "delete", True),
        ("owner", "edit", True),
        ("owner", "view", True),
        ("editor", "edit", True),
        ("editor", "view", True),
        ("editor", "add_member", False),
        ("editor", "delete", False),
        ("viewer", "view", True),
        ("viewer", "edit", False),
        ("viewer", "add_member", False),
        ("viewer", "delete", False)
    ])
    async def test_check_user_project_action_permission_calls_validate(self, mocker, role, action_type, expected_allowed):
        # Mock PermissionService.validate_project_action_by_role
        permission_service = PermissionService()
        mock_validate = mocker.patch.object(permission_service, "validate_project_action_by_role", return_value=(expected_allowed, None if expected_allowed else f"Ação '{action_type}' não permitida para role '{role}'."))
        # Mock user e project
        mocker.patch.object(permission_service, "mongo_service")
        mocker.patch.object(permission_service.mongo_service, "get_user_by_email", return_value=asyncio.Future())
        permission_service.mongo_service.get_user_by_email.return_value.set_result(type("User", (), {"active": True, "company_id": "company-1", "email": "user@example.com"})())
        mocker.patch.object(permission_service.mongo_service, "get_project_by_id", return_value=asyncio.Future())
        permission_service.mongo_service.get_project_by_id.return_value.set_result(type("Project", (), {"members": [type("Member", (), {"email": "user@example.com", "role": role})()]})())
        req_email = "user@example.com"
        project_id = "project-1"
        result = await permission_service.check_user_project_action_permission(req_email, project_id, action_type)
        assert result[0] == expected_allowed
        mock_validate.assert_called_once_with(role, action_type)

    async def test_check_user_project_action_permission_invalid_role(self, mocker):
        permission_service = PermissionService()
        mock_validate = mocker.patch.object(permission_service, "validate_project_action_by_role", return_value=(False, "Role 'invalid_role' não reconhecida."))
        mocker.patch.object(permission_service, "mongo_service")
        mocker.patch.object(permission_service.mongo_service, "get_user_by_email", return_value=asyncio.Future())
        permission_service.mongo_service.get_user_by_email.return_value.set_result(type("User", (), {"active": True, "company_id": "company-1", "email": "user@example.com"})())
        mocker.patch.object(permission_service.mongo_service, "get_project_by_id", return_value=asyncio.Future())
        permission_service.mongo_service.get_project_by_id.return_value.set_result(type("Project", (), {"members": [type("Member", (), {"email": "user@example.com", "role": "invalid_role"})()]})())
        req_email = "user@example.com"
        project_id = "project-1"
        result = await permission_service.check_user_project_action_permission(req_email, project_id, "view")
        assert result[0] is False
        assert result[2] == "Role 'invalid_role' não reconhecida."
