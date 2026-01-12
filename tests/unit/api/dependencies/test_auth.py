"""Tests for authentication dependencies."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from applicant_validator.api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_superadmin,
)


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_cookie(self) -> None:
        """Should return None when no session cookie."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_session = AsyncMock()

        with patch(
            "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
        ) as mock_cache:
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_invalid_token(self) -> None:
        """Should return None when token is invalid."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "invalid_token"
        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
            ) as mock_cache,
            patch(
                "applicant_validator.api.dependencies.auth.decode_jwt_token",
                return_value=None,
            ),
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_missing_payload_fields(self) -> None:
        """Should return None when payload is missing sub or jti."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "valid_token"
        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
            ) as mock_cache,
            patch(
                "applicant_validator.api.dependencies.auth.decode_jwt_token",
                return_value={"sub": None, "jti": None},
            ),
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_session_invalid(self) -> None:
        """Should return None when session is revoked or expired."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "valid_token"
        mock_session = AsyncMock()
        user_id = str(uuid.uuid4())

        with (
            patch(
                "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
            ) as mock_cache,
            patch(
                "applicant_validator.api.dependencies.auth.decode_jwt_token",
                return_value={"sub": user_id, "jti": "session_id"},
            ),
            patch(
                "applicant_validator.api.dependencies.auth.validate_session",
                return_value=None,
            ),
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self) -> None:
        """Should return user when fully authenticated."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "valid_token"
        mock_session = AsyncMock()
        user_id = str(uuid.uuid4())
        mock_user = MagicMock()
        mock_user.is_active = True

        with (
            patch(
                "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
            ) as mock_cache,
            patch(
                "applicant_validator.api.dependencies.auth.decode_jwt_token",
                return_value={"sub": user_id, "jti": "session_id"},
            ),
            patch(
                "applicant_validator.api.dependencies.auth.validate_session",
                return_value=MagicMock(),
            ),
            patch(
                "applicant_validator.api.dependencies.auth.get_user_by_id",
                return_value=mock_user,
            ),
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_none_when_user_inactive(self) -> None:
        """Should return None when user is inactive."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "valid_token"
        mock_session = AsyncMock()
        user_id = str(uuid.uuid4())
        mock_user = MagicMock()
        mock_user.is_active = False

        with (
            patch(
                "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
            ) as mock_cache,
            patch(
                "applicant_validator.api.dependencies.auth.decode_jwt_token",
                return_value={"sub": user_id, "jti": "session_id"},
            ),
            patch(
                "applicant_validator.api.dependencies.auth.validate_session",
                return_value=MagicMock(),
            ),
            patch(
                "applicant_validator.api.dependencies.auth.get_user_by_id",
                return_value=mock_user,
            ),
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_invalid_user_id(self) -> None:
        """Should return None when user_id is not a valid UUID."""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "valid_token"
        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.api.dependencies.auth.get_auth_settings_cache"
            ) as mock_cache,
            patch(
                "applicant_validator.api.dependencies.auth.decode_jwt_token",
                return_value={"sub": "not-a-uuid", "jti": "session_id"},
            ),
            patch(
                "applicant_validator.api.dependencies.auth.validate_session",
                return_value=MagicMock(),
            ),
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.cookie_name = "session"
            mock_cache.return_value = mock_cache_instance

            result = await get_current_user_optional(mock_request, mock_session)

        assert result is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self) -> None:
        """Should return user when authenticated."""
        mock_user = MagicMock()

        result = await get_current_user(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_raises_401_when_not_authenticated(self) -> None:
        """Should raise 401 when not authenticated."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_when_admin(self) -> None:
        """Should return user when user is admin."""
        mock_user = MagicMock()
        mock_user.is_admin = True

        result = await require_admin(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_user_when_superadmin(self) -> None:
        """Should return user when user is superadmin (also admin)."""
        mock_user = MagicMock()
        mock_user.is_admin = True  # Superadmins have is_admin = True

        result = await require_admin(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_raises_403_when_not_admin(self) -> None:
        """Should raise 403 when user is not admin."""
        mock_user = MagicMock()
        mock_user.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)

        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail


class TestRequireSuperadmin:
    """Tests for require_superadmin dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_when_superadmin(self) -> None:
        """Should return user when user is superadmin."""
        mock_user = MagicMock()
        mock_user.is_superadmin = True

        result = await require_superadmin(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_raises_403_when_not_superadmin(self) -> None:
        """Should raise 403 when user is not superadmin."""
        mock_user = MagicMock()
        mock_user.is_superadmin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_superadmin(mock_user)

        assert exc_info.value.status_code == 403
        assert "Superadmin privileges required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_403_when_admin_but_not_superadmin(self) -> None:
        """Should raise 403 when user is admin but not superadmin."""
        mock_user = MagicMock()
        mock_user.is_admin = True
        mock_user.is_superadmin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_superadmin(mock_user)

        assert exc_info.value.status_code == 403
