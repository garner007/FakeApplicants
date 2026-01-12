"""Tests for auth service functions."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from applicant_validator.database import User, UserRole
from applicant_validator.services.auth import (
    authenticate_user,
    change_email,
    change_password,
    complete_initial_setup,
    create_jwt_token,
    create_session,
    create_user,
    decode_jwt_token,
    generate_temp_password,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    reset_user_password,
    revoke_all_user_sessions,
    revoke_session,
    validate_email_domain,
    validate_session,
    verify_password,
)


class TestHashPassword:
    """Tests for hash_password function."""

    def test_returns_hash_string(self) -> None:
        """Should return a hashed password string."""
        result = hash_password("mypassword123")
        assert isinstance(result, str)
        assert result != "mypassword123"

    def test_different_passwords_produce_different_hashes(self) -> None:
        """Should produce different hashes for different passwords."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self) -> None:
        """Should produce different hashes due to salt."""
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        # Bcrypt uses random salt, so same password produces different hashes
        assert hash1 != hash2

    def test_hash_starts_with_bcrypt_prefix(self) -> None:
        """Should produce bcrypt-formatted hash."""
        result = hash_password("testpass")
        assert result.startswith("$2")


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_correct_password_returns_true(self) -> None:
        """Should return True for correct password."""
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_incorrect_password_returns_false(self) -> None:
        """Should return False for incorrect password."""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_returns_false(self) -> None:
        """Should return False for empty password."""
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False


class TestValidateEmailDomain:
    """Tests for validate_email_domain function."""

    def test_allows_all_when_no_restriction(self) -> None:
        """Should allow all emails when no domain restriction."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.allowed_domain = ""
            mock_cache_fn.return_value = cache

            assert validate_email_domain("test@example.com") is True
            assert validate_email_domain("user@gmail.com") is True

    def test_allows_matching_domain(self) -> None:
        """Should allow email from matching domain."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.allowed_domain = "company.com"
            mock_cache_fn.return_value = cache

            assert validate_email_domain("user@company.com") is True

    def test_rejects_non_matching_domain(self) -> None:
        """Should reject email from non-matching domain."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.allowed_domain = "company.com"
            mock_cache_fn.return_value = cache

            assert validate_email_domain("user@gmail.com") is False

    def test_case_insensitive_comparison(self) -> None:
        """Should be case insensitive."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.allowed_domain = "Company.Com"
            mock_cache_fn.return_value = cache

            assert validate_email_domain("user@company.com") is True
            assert validate_email_domain("user@COMPANY.COM") is True

    def test_rejects_invalid_email_format(self) -> None:
        """Should reject email without @ symbol."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.allowed_domain = "company.com"
            mock_cache_fn.return_value = cache

            assert validate_email_domain("invalid-email") is False


class TestGenerateTempPassword:
    """Tests for generate_temp_password function."""

    def test_default_length_is_16(self) -> None:
        """Should generate 16-character password by default."""
        password = generate_temp_password()
        assert len(password) == 16

    def test_custom_length(self) -> None:
        """Should generate password of specified length."""
        password = generate_temp_password(length=24)
        assert len(password) == 24

    def test_contains_only_alphanumeric(self) -> None:
        """Should contain only alphanumeric characters."""
        password = generate_temp_password()
        assert password.isalnum()

    def test_generates_different_passwords(self) -> None:
        """Should generate unique passwords each time."""
        password1 = generate_temp_password()
        password2 = generate_temp_password()
        assert password1 != password2


class TestCreateJwtToken:
    """Tests for create_jwt_token function."""

    def test_returns_string_token(self) -> None:
        """Should return a JWT token string."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "test_secret_key_12345"  # pragma: allowlist secret
            cache.jwt_expiry_hours = 24
            mock_cache_fn.return_value = cache

            token = create_jwt_token("user123", "jti456")
            assert isinstance(token, str)
            assert len(token) > 0

    def test_token_is_decodable(self) -> None:
        """Should create a token that can be decoded."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "test_secret_key_12345"  # pragma: allowlist secret
            cache.jwt_expiry_hours = 24
            mock_cache_fn.return_value = cache

            token = create_jwt_token("user123", "jti456")
            payload = decode_jwt_token(token)

            assert payload is not None
            assert payload["sub"] == "user123"
            assert payload["jti"] == "jti456"


class TestDecodeJwtToken:
    """Tests for decode_jwt_token function."""

    def test_returns_payload_for_valid_token(self) -> None:
        """Should return payload for valid token."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "test_secret_key_12345"  # pragma: allowlist secret
            cache.jwt_expiry_hours = 24
            mock_cache_fn.return_value = cache

            token = create_jwt_token("user123", "jti456")
            payload = decode_jwt_token(token)

            assert payload is not None
            assert "sub" in payload
            assert "jti" in payload
            assert "exp" in payload

    def test_returns_none_for_invalid_token(self) -> None:
        """Should return None for invalid token."""
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "test_secret"  # pragma: allowlist secret
            mock_cache_fn.return_value = cache

            payload = decode_jwt_token("invalid_token_string")
            assert payload is None

    def test_returns_none_for_wrong_secret(self) -> None:
        """Should return None when decoded with wrong secret."""
        # Create token with one secret
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "secret1"  # pragma: allowlist secret
            cache.jwt_expiry_hours = 24
            mock_cache_fn.return_value = cache
            token = create_jwt_token("user123", "jti456")

        # Try to decode with different secret
        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "secret2"  # pragma: allowlist secret
            mock_cache_fn.return_value = cache
            payload = decode_jwt_token(token)
            assert payload is None


class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    @pytest.mark.asyncio
    async def test_returns_user_when_found(self) -> None:
        """Should return user when found."""
        mock_user = MagicMock(spec=User)
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_email(mock_session, "test@example.com")

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        """Should return None when user not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_email(mock_session, "nonexistent@example.com")

        assert result is None


class TestGetUserById:
    """Tests for get_user_by_id function."""

    @pytest.mark.asyncio
    async def test_returns_user_when_found(self) -> None:
        """Should return user when found."""
        user_id = uuid.uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_id(mock_session, user_id)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        """Should return None when user not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_id(mock_session, uuid.uuid4())

        assert result is None


class TestAuthenticateUser:
    """Tests for authenticate_user function."""

    @pytest.mark.asyncio
    async def test_returns_user_for_valid_credentials(self) -> None:
        """Should return user for valid email and password."""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = True
        mock_user.password_hash = hash_password("correctpassword")

        mock_session = AsyncMock()

        with patch(
            "applicant_validator.services.auth.get_user_by_email",
            return_value=mock_user,
        ):
            result = await authenticate_user(mock_session, "test@example.com", "correctpassword")

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_password(self) -> None:
        """Should return None for incorrect password."""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = True
        mock_user.password_hash = hash_password("correctpassword")

        mock_session = AsyncMock()

        with patch(
            "applicant_validator.services.auth.get_user_by_email",
            return_value=mock_user,
        ):
            result = await authenticate_user(mock_session, "test@example.com", "wrongpassword")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_user(self) -> None:
        """Should return None when user doesn't exist."""
        mock_session = AsyncMock()

        with patch(
            "applicant_validator.services.auth.get_user_by_email",
            return_value=None,
        ):
            result = await authenticate_user(mock_session, "nonexistent@example.com", "password")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_inactive_user(self) -> None:
        """Should return None for inactive user."""
        mock_user = MagicMock(spec=User)
        mock_user.is_active = False
        mock_user.password_hash = hash_password("password")

        mock_session = AsyncMock()

        with patch(
            "applicant_validator.services.auth.get_user_by_email",
            return_value=mock_user,
        ):
            result = await authenticate_user(mock_session, "test@example.com", "password")

        assert result is None


class TestCreateSession:
    """Tests for create_session function."""

    @pytest.mark.asyncio
    async def test_creates_session_and_returns_token(self) -> None:
        """Should create session and return JWT token."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()
        mock_user.last_login_at = None

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "test_secret"  # pragma: allowlist secret
            cache.jwt_expiry_hours = 24
            mock_cache_fn.return_value = cache

            token, _user_session = await create_session(
                mock_session,
                mock_user,
                ip_address="192.168.1.1",
                user_agent="TestBrowser/1.0",
            )

        assert isinstance(token, str)
        assert len(token) > 0
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_last_login_at(self) -> None:
        """Should update user's last_login_at."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()
        mock_user.last_login_at = None

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn:
            cache = MagicMock()
            cache.jwt_secret = "test_secret"  # pragma: allowlist secret
            cache.jwt_expiry_hours = 24
            mock_cache_fn.return_value = cache

            await create_session(mock_session, mock_user)

        assert mock_user.last_login_at is not None


class TestValidateSession:
    """Tests for validate_session function."""

    @pytest.mark.asyncio
    async def test_returns_session_when_valid(self) -> None:
        """Should return session when valid and not revoked."""
        mock_session_record = MagicMock()
        mock_session_record.is_revoked = False
        mock_session_record.expires_at = datetime.now(UTC) + timedelta(hours=1)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await validate_session(mock_session, "jti123")

        assert result == mock_session_record

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        """Should return None when session not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await validate_session(mock_session, "nonexistent")

        assert result is None


class TestRevokeSession:
    """Tests for revoke_session function."""

    @pytest.mark.asyncio
    async def test_revokes_existing_session(self) -> None:
        """Should mark session as revoked."""
        mock_session_record = MagicMock()
        mock_session_record.is_revoked = False
        mock_session_record.revoked_at = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await revoke_session(mock_session, "jti123")

        assert result is True
        assert mock_session_record.is_revoked is True
        assert mock_session_record.revoked_at is not None

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self) -> None:
        """Should return False when session not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await revoke_session(mock_session, "nonexistent")

        assert result is False


class TestRevokeAllUserSessions:
    """Tests for revoke_all_user_sessions function."""

    @pytest.mark.asyncio
    async def test_revokes_all_active_sessions(self) -> None:
        """Should revoke all active sessions for user."""
        mock_session1 = MagicMock()
        mock_session1.is_revoked = False
        mock_session2 = MagicMock()
        mock_session2.is_revoked = False

        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_session1, mock_session2]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        count = await revoke_all_user_sessions(mock_db_session, uuid.uuid4())

        assert count == 2
        assert mock_session1.is_revoked is True
        assert mock_session2.is_revoked is True

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_sessions(self) -> None:
        """Should return 0 when user has no sessions."""
        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        count = await revoke_all_user_sessions(mock_db_session, uuid.uuid4())

        assert count == 0


class TestCreateUser:
    """Tests for create_user function."""

    @pytest.mark.asyncio
    async def test_creates_user_successfully(self) -> None:
        """Should create user with hashed password."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with (
            patch(
                "applicant_validator.services.auth.validate_email_domain",
                return_value=True,
            ),
            patch(
                "applicant_validator.services.auth.get_user_by_email",
                return_value=None,
            ),
        ):
            user = await create_user(
                mock_session,
                email="newuser@example.com",
                password="password123",  # pragma: allowlist secret
                name="New User",
                role=UserRole.USER,
            )

        assert user.email == "newuser@example.com"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_domain(self) -> None:
        """Should raise ValueError for invalid email domain."""
        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.services.auth.validate_email_domain",
                return_value=False,
            ),
            patch("applicant_validator.services.auth.get_auth_settings_cache") as mock_cache_fn,
        ):
            cache = MagicMock()
            cache.allowed_domain = "company.com"
            mock_cache_fn.return_value = cache

            with pytest.raises(ValueError) as exc_info:
                await create_user(
                    mock_session,
                    email="user@other.com",
                    password="password",  # pragma: allowlist secret
                    name="Test",
                )

            assert "domain" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_raises_error_for_existing_email(self) -> None:
        """Should raise ValueError when email already exists."""
        mock_session = AsyncMock()
        mock_existing_user = MagicMock(spec=User)

        with (
            patch(
                "applicant_validator.services.auth.validate_email_domain",
                return_value=True,
            ),
            patch(
                "applicant_validator.services.auth.get_user_by_email",
                return_value=mock_existing_user,
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                await create_user(
                    mock_session,
                    email="existing@example.com",
                    password="password",  # pragma: allowlist secret
                    name="Test",
                )

            assert "already registered" in str(exc_info.value).lower()


class TestChangePassword:
    """Tests for change_password function."""

    @pytest.mark.asyncio
    async def test_updates_password_hash(self) -> None:
        """Should update user's password hash."""
        mock_user = MagicMock(spec=User)
        mock_user.password_hash = "old_hash"  # pragma: allowlist secret
        mock_user.must_change_password = True

        mock_session = AsyncMock()

        await change_password(mock_session, mock_user, "newpassword123")

        assert mock_user.password_hash != "old_hash"  # pragma: allowlist secret
        assert mock_user.must_change_password is False


class TestChangeEmail:
    """Tests for change_email function."""

    @pytest.mark.asyncio
    async def test_updates_email(self) -> None:
        """Should update user's email."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()
        mock_user.email = "old@example.com"
        mock_user.must_change_email = True

        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.services.auth.validate_email_domain",
                return_value=True,
            ),
            patch(
                "applicant_validator.services.auth.get_user_by_email",
                return_value=None,
            ),
        ):
            await change_email(mock_session, mock_user, "new@example.com")

        assert mock_user.email == "new@example.com"
        assert mock_user.must_change_email is False

    @pytest.mark.asyncio
    async def test_raises_error_for_existing_email(self) -> None:
        """Should raise ValueError when new email already exists."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()

        mock_other_user = MagicMock(spec=User)
        mock_other_user.id = uuid.uuid4()

        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.services.auth.validate_email_domain",
                return_value=True,
            ),
            patch(
                "applicant_validator.services.auth.get_user_by_email",
                return_value=mock_other_user,
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                await change_email(mock_session, mock_user, "taken@example.com")

            assert "already registered" in str(exc_info.value).lower()


class TestCompleteInitialSetup:
    """Tests for complete_initial_setup function."""

    @pytest.mark.asyncio
    async def test_changes_both_email_and_password(self) -> None:
        """Should change both email and password when required."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()
        mock_user.must_change_email = True
        mock_user.must_change_password = True

        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.services.auth.change_email", new_callable=AsyncMock
            ) as mock_change_email,
            patch(
                "applicant_validator.services.auth.change_password",
                new_callable=AsyncMock,
            ) as mock_change_password,
        ):
            await complete_initial_setup(
                mock_session, mock_user, "new@example.com", "newpassword123"
            )

        mock_change_email.assert_called_once()
        mock_change_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_error_when_email_required_but_not_provided(self) -> None:
        """Should raise ValueError when email change required but not provided."""
        mock_user = MagicMock(spec=User)
        mock_user.must_change_email = True

        mock_session = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await complete_initial_setup(mock_session, mock_user, None, "newpassword123")

        assert "email change is required" in str(exc_info.value).lower()


class TestResetUserPassword:
    """Tests for reset_user_password function."""

    @pytest.mark.asyncio
    async def test_generates_new_temp_password(self) -> None:
        """Should generate new temp password and revoke sessions."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid.uuid4()
        mock_user.password_hash = "old_hash"  # pragma: allowlist secret
        mock_user.must_change_password = False

        mock_session = AsyncMock()

        with patch(
            "applicant_validator.services.auth.revoke_all_user_sessions",
            new_callable=AsyncMock,
        ) as mock_revoke:
            temp_password = await reset_user_password(mock_session, mock_user)

        assert len(temp_password) == 16
        assert mock_user.must_change_password is True
        mock_revoke.assert_called_once()
