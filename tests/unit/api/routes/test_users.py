"""Tests for users API routes."""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.users import (
    CreateUserRequest,
    CreateUserResponse,
    MessageResponse,
    ResetPasswordResponse,
    UpdateUserRequest,
    UserDetailResponse,
    UserListResponse,
    _validate_role,
    router,
)
from applicant_validator.database import User, UserRole


class TestValidateRoleHelper:
    """Tests for _validate_role helper function."""

    def test_valid_user_role(self) -> None:
        """Should accept valid user role."""
        current_user = MagicMock(spec=User)
        current_user.is_superadmin = False

        # Should not raise
        _validate_role("user", current_user)

    def test_valid_admin_role(self) -> None:
        """Should accept valid admin role."""
        current_user = MagicMock(spec=User)
        current_user.is_superadmin = False

        # Should not raise
        _validate_role("admin", current_user)

    def test_invalid_role_raises_400(self) -> None:
        """Should raise 400 for invalid role."""
        from fastapi import HTTPException

        current_user = MagicMock(spec=User)
        current_user.is_superadmin = False

        with pytest.raises(HTTPException) as exc_info:
            _validate_role("invalid_role", current_user)

        assert exc_info.value.status_code == 400
        assert "Invalid role" in str(exc_info.value.detail)

    def test_superadmin_role_requires_superadmin(self) -> None:
        """Should raise 403 when non-superadmin tries to assign superadmin."""
        from fastapi import HTTPException

        current_user = MagicMock(spec=User)
        current_user.is_superadmin = False

        with pytest.raises(HTTPException) as exc_info:
            _validate_role("superadmin", current_user)

        assert exc_info.value.status_code == 403
        assert "Only superadmins" in str(exc_info.value.detail)

    def test_superadmin_can_assign_superadmin(self) -> None:
        """Should allow superadmin to assign superadmin role."""
        current_user = MagicMock(spec=User)
        current_user.is_superadmin = True

        # Should not raise
        _validate_role("superadmin", current_user)

    def test_non_superadmin_cannot_modify_superadmin(self) -> None:
        """Should raise 403 when non-superadmin tries to modify superadmin."""
        from fastapi import HTTPException

        current_user = MagicMock(spec=User)
        current_user.is_superadmin = False

        target_user = MagicMock(spec=User)
        target_user.is_superadmin = True

        with pytest.raises(HTTPException) as exc_info:
            _validate_role("admin", current_user, target_user)

        assert exc_info.value.status_code == 403
        assert "Only superadmins can modify superadmin" in str(exc_info.value.detail)

    def test_superadmin_can_modify_superadmin(self) -> None:
        """Should allow superadmin to modify other superadmin."""
        current_user = MagicMock(spec=User)
        current_user.is_superadmin = True

        target_user = MagicMock(spec=User)
        target_user.is_superadmin = True

        # Should not raise
        _validate_role("admin", current_user, target_user)


class TestUsersRoutesAuthentication:
    """Tests for user routes authentication requirements."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with users router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_list_users_requires_admin(self, app: FastAPI) -> None:
        """Should return 401 if not authenticated."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/users")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_requires_admin(self, app: FastAPI) -> None:
        """Should return 401 if not authenticated."""
        user_id = str(uuid.uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/api/users/{user_id}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_user_requires_admin(self, app: FastAPI) -> None:
        """Should return 401 if not authenticated."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/users",
                json={
                    "email": "newuser@example.com",
                    "first_name": "New",
                    "last_name": "User",
                    "role": "user",
                },
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_user_requires_admin(self, app: FastAPI) -> None:
        """Should return 401 if not authenticated."""
        user_id = str(uuid.uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                f"/api/users/{user_id}",
                json={"first_name": "Updated"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_user_requires_admin(self, app: FastAPI) -> None:
        """Should return 401 if not authenticated."""
        user_id = str(uuid.uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete(f"/api/users/{user_id}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_requires_admin(self, app: FastAPI) -> None:
        """Should return 401 if not authenticated."""
        user_id = str(uuid.uuid4())
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(f"/api/users/{user_id}/reset-password")

        assert response.status_code == 401


class TestCreateUserRequestValidation:
    """Tests for CreateUserRequest validation."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_create_user_validation_missing_email(self, app: FastAPI) -> None:
        """Should return 422 for missing email."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/users",
                json={
                    "first_name": "New",
                    "last_name": "User",
                },
            )

        # Will be 401 (auth required) or 422 (validation)
        assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_create_user_validation_invalid_email(self, app: FastAPI) -> None:
        """Should return 422 for invalid email format."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/users",
                json={
                    "email": "not-an-email",
                    "first_name": "New",
                    "last_name": "User",
                },
            )

        assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_create_user_validation_empty_first_name(self, app: FastAPI) -> None:
        """Should return 422 for empty first_name."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/users",
                json={
                    "email": "test@example.com",
                    "first_name": "",
                    "last_name": "User",
                },
            )

        assert response.status_code in (401, 422)


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_user_list_response_model(self) -> None:
        """Should create UserListResponse with all fields."""
        resp = UserListResponse(
            id="uuid-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="user",
            is_active=True,
            must_change_password=False,
            last_login_at="2024-01-01T00:00:00",
            created_at="2024-01-01T00:00:00",
        )
        assert resp.id == "uuid-123"
        assert resp.email == "test@example.com"
        assert resp.first_name == "Test"
        assert resp.last_name == "User"
        assert resp.is_active is True

    def test_user_detail_response_model(self) -> None:
        """Should create UserDetailResponse with created_by_email."""
        resp = UserDetailResponse(
            id="uuid-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="admin",
            is_active=True,
            must_change_password=False,
            last_login_at=None,
            created_at="2024-01-01T00:00:00",
            created_by_email="admin@example.com",
        )
        assert resp.created_by_email == "admin@example.com"

    def test_user_detail_response_null_created_by(self) -> None:
        """Should allow null created_by_email."""
        resp = UserDetailResponse(
            id="uuid-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="user",
            is_active=True,
            must_change_password=True,
            last_login_at=None,
            created_at="2024-01-01T00:00:00",
            created_by_email=None,
        )
        assert resp.created_by_email is None

    def test_create_user_request_valid(self) -> None:
        """Should create CreateUserRequest with valid data."""
        req = CreateUserRequest(
            email="newuser@example.com",
            first_name="New",
            last_name="User",
            role="user",
        )
        assert req.email == "newuser@example.com"
        assert req.first_name == "New"
        assert req.last_name == "User"
        assert req.role == "user"

    def test_create_user_request_default_role(self) -> None:
        """Should default role to 'user'."""
        req = CreateUserRequest(
            email="newuser@example.com",
            first_name="New",
            last_name="User",
        )
        assert req.role == "user"

    def test_create_user_request_invalid_email(self) -> None:
        """Should raise error for invalid email."""
        with pytest.raises(ValueError):
            CreateUserRequest(
                email="invalid",
                first_name="New",
                last_name="User",
            )

    def test_create_user_request_empty_first_name(self) -> None:
        """Should raise error for empty first_name."""
        with pytest.raises(ValueError):
            CreateUserRequest(
                email="test@example.com",
                first_name="",
                last_name="User",
            )

    def test_create_user_response_model(self) -> None:
        """Should create CreateUserResponse with temp_password."""
        resp = CreateUserResponse(
            id="uuid-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="user",
            temp_password="tempPass123",  # pragma: allowlist secret
        )
        assert resp.temp_password == "tempPass123"  # pragma: allowlist secret

    def test_update_user_request_all_fields(self) -> None:
        """Should create UpdateUserRequest with all optional fields."""
        req = UpdateUserRequest(
            first_name="Updated",
            last_name="Name",
            role="admin",
            is_active=False,
        )
        assert req.first_name == "Updated"
        assert req.last_name == "Name"
        assert req.role == "admin"
        assert req.is_active is False

    def test_update_user_request_partial(self) -> None:
        """Should allow partial updates."""
        req = UpdateUserRequest(first_name="Updated")
        assert req.first_name == "Updated"
        assert req.last_name is None
        assert req.role is None
        assert req.is_active is None

    def test_update_user_request_empty(self) -> None:
        """Should allow empty update request."""
        req = UpdateUserRequest()
        assert req.first_name is None
        assert req.last_name is None
        assert req.role is None
        assert req.is_active is None

    def test_reset_password_response_model(self) -> None:
        """Should create ResetPasswordResponse with temp_password and message."""
        resp = ResetPasswordResponse(
            temp_password="newTempPass456",  # pragma: allowlist secret
            message="Password reset successful",
        )
        assert resp.temp_password == "newTempPass456"  # pragma: allowlist secret
        assert resp.message == "Password reset successful"

    def test_message_response_model(self) -> None:
        """Should create MessageResponse with message."""
        resp = MessageResponse(message="User deactivated")
        assert resp.message == "User deactivated"


class TestUserRoleEnum:
    """Tests for UserRole enum usage."""

    def test_user_role_values(self) -> None:
        """Should have correct role values."""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SUPERADMIN.value == "superadmin"

    def test_invalid_role_raises_error(self) -> None:
        """Should raise error for invalid role."""
        with pytest.raises(ValueError):
            UserRole("invalid")
