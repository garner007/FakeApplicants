"""Tests for the auth settings service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from applicant_validator.services.auth_settings import (
    AUTH_DEFAULTS,
    AuthSettingsCache,
    _get_setting_description,
    _get_setting_type,
    ensure_auth_settings,
    generate_jwt_secret,
    get_all_auth_settings,
    get_auth_setting,
    get_auth_settings_cache,
    get_jwt_secret,
    set_auth_setting,
)


class TestAuthDefaults:
    """Tests for AUTH_DEFAULTS constant."""

    def test_has_required_settings(self) -> None:
        """Should have all required auth settings."""
        assert "auth_allowed_domain" in AUTH_DEFAULTS
        assert "auth_jwt_expiry_hours" in AUTH_DEFAULTS
        assert "auth_cookie_name" in AUTH_DEFAULTS
        assert "auth_cookie_secure" in AUTH_DEFAULTS
        assert "auth_min_password_length" in AUTH_DEFAULTS

    def test_default_values_are_strings(self) -> None:
        """All default values should be strings."""
        for value in AUTH_DEFAULTS.values():
            assert isinstance(value, str)


class TestGetAuthSetting:
    """Tests for get_auth_setting function."""

    @pytest.mark.asyncio
    async def test_returns_value_when_found(self) -> None:
        """Should return setting value from database."""
        mock_config = MagicMock()
        mock_config.value = "test_value"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_auth_setting(mock_session, "auth_allowed_domain")

        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_returns_default_when_not_found(self) -> None:
        """Should return default value when setting not in database."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_auth_setting(mock_session, "auth_allowed_domain")

        assert result == AUTH_DEFAULTS["auth_allowed_domain"]

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_key(self) -> None:
        """Should return empty string for unknown key not in defaults."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_auth_setting(mock_session, "unknown_key")

        assert result == ""


class TestGetAllAuthSettings:
    """Tests for get_all_auth_settings function."""

    @pytest.mark.asyncio
    async def test_returns_all_settings_with_defaults(self) -> None:
        """Should return all settings using defaults."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_all_auth_settings(mock_session)

        # Should have all default keys
        for key in AUTH_DEFAULTS:
            assert key in result

    @pytest.mark.asyncio
    async def test_overrides_defaults_with_db_values(self) -> None:
        """Should override defaults with database values."""
        mock_config = MagicMock()
        mock_config.key = "auth_allowed_domain"
        mock_config.value = "company.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_config]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_all_auth_settings(mock_session)

        assert result["auth_allowed_domain"] == "company.com"


class TestSetAuthSetting:
    """Tests for set_auth_setting function."""

    @pytest.mark.asyncio
    async def test_updates_existing_setting(self) -> None:
        """Should update existing setting in database."""
        mock_config = MagicMock()
        mock_config.value = "old_value"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        result = await set_auth_setting(mock_session, "auth_allowed_domain", "new_value")

        assert mock_config.value == "new_value"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_new_setting(self) -> None:
        """Should create new setting if not exists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        await set_auth_setting(mock_session, "auth_allowed_domain", "company.com")

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_invalid_key(self) -> None:
        """Should raise ValueError for invalid setting key."""
        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid auth setting key"):
            await set_auth_setting(mock_session, "invalid_key", "value")


class TestGenerateJwtSecret:
    """Tests for generate_jwt_secret function."""

    def test_generates_64_char_hex(self) -> None:
        """Should generate 64-character hex string."""
        secret = generate_jwt_secret()

        assert len(secret) == 64
        assert all(c in "0123456789abcdef" for c in secret)

    def test_generates_unique_secrets(self) -> None:
        """Should generate unique secrets on each call."""
        secrets_list = [generate_jwt_secret() for _ in range(5)]

        assert len(set(secrets_list)) == 5


class TestGetJwtSecret:
    """Tests for get_jwt_secret function."""

    @pytest.mark.asyncio
    async def test_returns_existing_secret(self) -> None:
        """Should return existing JWT secret from database."""
        mock_config = MagicMock()
        mock_config.value = "existing_secret"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_jwt_secret(mock_session)

        assert result == "existing_secret"

    @pytest.mark.asyncio
    async def test_generates_and_stores_new_secret(self) -> None:
        """Should generate and store new secret if none exists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        result = await get_jwt_secret(mock_session)

        # Should return a valid 64-char hex secret
        assert len(result) == 64
        mock_session.add.assert_called_once()


class TestEnsureAuthSettings:
    """Tests for ensure_auth_settings function."""

    @pytest.mark.asyncio
    async def test_creates_missing_settings(self) -> None:
        """Should create missing auth settings with defaults."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        await ensure_auth_settings(mock_session)

        # Should have called add for JWT secret + default settings
        assert mock_session.add.call_count >= len(AUTH_DEFAULTS)


class TestGetSettingDescription:
    """Tests for _get_setting_description function."""

    def test_returns_description_for_known_keys(self) -> None:
        """Should return description for known setting keys."""
        desc = _get_setting_description("auth_allowed_domain")
        assert "domain" in desc.lower()

        desc = _get_setting_description("auth_jwt_expiry_hours")
        assert "expiry" in desc.lower()

    def test_returns_empty_for_unknown_key(self) -> None:
        """Should return empty string for unknown key."""
        desc = _get_setting_description("unknown_key")
        assert desc == ""


class TestGetSettingType:
    """Tests for _get_setting_type function."""

    def test_returns_type_for_known_keys(self) -> None:
        """Should return correct type for known setting keys."""
        assert _get_setting_type("auth_allowed_domain") == "string"
        assert _get_setting_type("auth_jwt_expiry_hours") == "integer"
        assert _get_setting_type("auth_cookie_secure") == "boolean"

    def test_returns_string_for_unknown_key(self) -> None:
        """Should return 'string' for unknown key."""
        assert _get_setting_type("unknown_key") == "string"


class TestAuthSettingsCache:
    """Tests for AuthSettingsCache class."""

    def test_singleton_pattern(self) -> None:
        """Should return same instance on multiple calls."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache1 = AuthSettingsCache()
        cache2 = AuthSettingsCache()

        assert cache1 is cache2

    def test_jwt_secret_raises_when_not_loaded(self) -> None:
        """Should raise RuntimeError when accessing jwt_secret before load."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()

        with pytest.raises(RuntimeError, match="not loaded"):
            _ = cache.jwt_secret

    def test_allowed_domain_property(self) -> None:
        """Should return allowed domain setting."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_allowed_domain": "company.com"}

        assert cache.allowed_domain == "company.com"

    def test_jwt_expiry_hours_property(self) -> None:
        """Should return JWT expiry hours as int."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_jwt_expiry_hours": "48"}

        assert cache.jwt_expiry_hours == 48

    def test_jwt_expiry_hours_invalid_returns_default(self) -> None:
        """Should return 24 when invalid value."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_jwt_expiry_hours": "invalid"}

        assert cache.jwt_expiry_hours == 24

    def test_cookie_name_property(self) -> None:
        """Should return cookie name setting."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_cookie_name": "my_session"}

        assert cache.cookie_name == "my_session"

    def test_cookie_secure_property_true(self) -> None:
        """Should return True for truthy values."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_cookie_secure": "true"}

        assert cache.cookie_secure is True

    def test_cookie_secure_property_false(self) -> None:
        """Should return False for falsy values."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_cookie_secure": "false"}

        assert cache.cookie_secure is False

    def test_min_password_length_property(self) -> None:
        """Should return min password length as int."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_min_password_length": "12"}

        assert cache.min_password_length == 12

    def test_min_password_length_invalid_returns_default(self) -> None:
        """Should return 8 when invalid value."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache._settings = {"auth_min_password_length": "invalid"}  # pragma: allowlist secret

        assert cache.min_password_length == 8

    @pytest.mark.asyncio
    async def test_load_method(self) -> None:
        """Should load settings from database."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()

        mock_session = AsyncMock()

        with (
            patch(
                "applicant_validator.services.auth_settings.get_jwt_secret",
                return_value="test_secret",
            ),
            patch(
                "applicant_validator.services.auth_settings.get_all_auth_settings",
                return_value={"auth_allowed_domain": "test.com"},
            ),
        ):
            await cache.load(mock_session)

        assert cache._jwt_secret == "test_secret"  # pragma: allowlist secret
        assert cache._loaded is True

    def test_refresh_sync(self) -> None:
        """Should refresh settings from provided dict."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()
        cache.refresh_sync({"auth_allowed_domain": "new.com"})

        assert cache._settings["auth_allowed_domain"] == "new.com"

    def test_is_loaded_property(self) -> None:
        """Should return loaded status."""
        # Reset singleton
        AuthSettingsCache._instance = None
        AuthSettingsCache._settings = {}
        AuthSettingsCache._jwt_secret = ""
        AuthSettingsCache._loaded = False

        cache = AuthSettingsCache()

        assert cache.is_loaded is False

        cache._loaded = True
        assert cache.is_loaded is True


class TestGetAuthSettingsCache:
    """Tests for get_auth_settings_cache function."""

    def test_returns_cache_instance(self) -> None:
        """Should return AuthSettingsCache instance."""
        result = get_auth_settings_cache()
        assert isinstance(result, AuthSettingsCache)
