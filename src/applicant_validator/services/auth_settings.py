"""Auth settings service - reads auth configuration from database.

Auth settings are stored in the SystemConfig table for easy management
through the admin panel. The JWT secret is auto-generated on first startup
and stored in the database (not editable via UI for security).
"""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database import SystemConfig

# Default values for auth settings
AUTH_DEFAULTS = {
    "auth_allowed_domain": "",  # Empty = allow all domains
    "auth_jwt_expiry_hours": "24",
    "auth_cookie_name": "session",
    "auth_cookie_secure": "false",
    "auth_min_password_length": "8",
}

# JWT secret key name - auto-generated, not user-editable
JWT_SECRET_KEY = "auth_jwt_secret"  # pragma: allowlist secret

# Auth settings keys
AUTH_SETTING_KEYS = list(AUTH_DEFAULTS.keys())


async def get_auth_setting(session: AsyncSession, key: str) -> str:
    """Get a single auth setting from the database.

    Args:
        session: Database session.
        key: Setting key.

    Returns:
        Setting value or default if not found.
    """
    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if config:
        return config.value

    return AUTH_DEFAULTS.get(key, "")


async def get_all_auth_settings(session: AsyncSession) -> dict[str, str]:
    """Get all auth settings from the database.

    Args:
        session: Database session.

    Returns:
        Dictionary of setting key -> value.
    """
    result = await session.execute(
        select(SystemConfig).where(SystemConfig.key.in_(AUTH_SETTING_KEYS))
    )
    configs = result.scalars().all()

    # Start with defaults
    settings = dict(AUTH_DEFAULTS)

    # Override with database values
    for config in configs:
        settings[config.key] = config.value

    return settings


async def set_auth_setting(
    session: AsyncSession,
    key: str,
    value: str,
) -> SystemConfig:
    """Set an auth setting in the database.

    Args:
        session: Database session.
        key: Setting key.
        value: Setting value.

    Returns:
        Updated SystemConfig instance.
    """
    if key not in AUTH_SETTING_KEYS:
        raise ValueError(f"Invalid auth setting key: {key}")

    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if config:
        config.value = value
    else:
        config = SystemConfig(
            key=key,
            value=value,
            description=_get_setting_description(key),
            value_type=_get_setting_type(key),
            category="auth",
            is_editable=True,
        )
        session.add(config)

    await session.flush()
    return config


def generate_jwt_secret() -> str:
    """Generate a cryptographically secure JWT secret.

    Returns:
        64-character hex string (256 bits of entropy).
    """
    return secrets.token_hex(32)


async def get_jwt_secret(session: AsyncSession) -> str:
    """Get the JWT secret from the database.

    If no secret exists, one will be auto-generated and stored.
    This ensures the secret persists across app restarts.

    Args:
        session: Database session.

    Returns:
        JWT secret string.
    """
    result = await session.execute(select(SystemConfig).where(SystemConfig.key == JWT_SECRET_KEY))
    config = result.scalar_one_or_none()

    if config:
        return config.value

    # Auto-generate and store a new secret
    new_secret = generate_jwt_secret()
    config = SystemConfig(
        key=JWT_SECRET_KEY,
        value=new_secret,
        description="Auto-generated JWT signing secret. Do not modify.",
        value_type="secret",
        category="auth",
        is_editable=False,  # Not editable via admin UI
    )
    session.add(config)
    await session.flush()

    return new_secret


async def ensure_auth_settings(session: AsyncSession) -> None:
    """Ensure all auth settings exist in the database with defaults.

    Called during startup or migration to seed default values.
    Also ensures JWT secret is generated.

    Args:
        session: Database session.
    """
    # Ensure JWT secret exists (auto-generate if needed)
    await get_jwt_secret(session)

    # Ensure other auth settings exist
    for key, default_value in AUTH_DEFAULTS.items():
        result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
        existing = result.scalar_one_or_none()

        if not existing:
            config = SystemConfig(
                key=key,
                value=default_value,
                description=_get_setting_description(key),
                value_type=_get_setting_type(key),
                category="auth",
                is_editable=True,
            )
            session.add(config)


def _get_setting_description(key: str) -> str:
    """Get description for an auth setting."""
    descriptions = {
        "auth_allowed_domain": "Email domain restriction (e.g., 'company.com'). Empty allows all.",
        "auth_jwt_expiry_hours": "JWT token expiry time in hours.",
        "auth_cookie_name": "Name of the HTTP-only session cookie.",
        "auth_cookie_secure": "Require HTTPS for session cookie (set 'true' in production).",
        "auth_min_password_length": "Minimum length for new passwords.",  # pragma: allowlist secret
    }
    return descriptions.get(key, "")


def _get_setting_type(key: str) -> str:
    """Get value type for an auth setting."""
    types = {
        "auth_allowed_domain": "string",
        "auth_jwt_expiry_hours": "integer",
        "auth_cookie_name": "string",
        "auth_cookie_secure": "boolean",
        "auth_min_password_length": "integer",  # pragma: allowlist secret
    }
    return types.get(key, "string")


# Synchronous helper for getting settings (uses cached values)
class AuthSettingsCache:
    """Cache for auth settings to avoid repeated database queries.

    Settings are loaded once and cached. Call refresh() to reload.
    The JWT secret is cached separately and immutable after first load.
    """

    _instance: "AuthSettingsCache | None" = None
    _settings: dict[str, str] = {}  # noqa: RUF012
    _jwt_secret: str = ""
    _loaded: bool = False

    def __new__(cls) -> "AuthSettingsCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def jwt_secret(self) -> str:
        """Get the JWT signing secret."""
        if not self._jwt_secret:
            raise RuntimeError("Auth settings not loaded. Call load() first during app startup.")
        return self._jwt_secret

    @property
    def allowed_domain(self) -> str:
        return self._settings.get("auth_allowed_domain", AUTH_DEFAULTS["auth_allowed_domain"])

    @property
    def jwt_expiry_hours(self) -> int:
        try:
            return int(
                self._settings.get("auth_jwt_expiry_hours", AUTH_DEFAULTS["auth_jwt_expiry_hours"])
            )
        except ValueError:
            return 24

    @property
    def cookie_name(self) -> str:
        return self._settings.get("auth_cookie_name", AUTH_DEFAULTS["auth_cookie_name"])

    @property
    def cookie_secure(self) -> bool:
        value = self._settings.get("auth_cookie_secure", AUTH_DEFAULTS["auth_cookie_secure"])
        return value.lower() in ("true", "1", "yes")

    @property
    def min_password_length(self) -> int:
        try:
            return int(
                self._settings.get(
                    "auth_min_password_length", AUTH_DEFAULTS["auth_min_password_length"]
                )
            )
        except ValueError:
            return 8

    async def load(self, session: AsyncSession) -> None:
        """Load settings from database.

        This also ensures the JWT secret exists (auto-generates if needed).
        """
        # Load or generate JWT secret
        self._jwt_secret = await get_jwt_secret(session)

        # Load other settings
        self._settings = await get_all_auth_settings(session)
        self._loaded = True

    def refresh_sync(self, settings: dict[str, str]) -> None:
        """Refresh cache with provided settings (for use after updates).

        Note: JWT secret cannot be refreshed - it's immutable once set.
        """
        self._settings = settings

    @property
    def is_loaded(self) -> bool:
        return self._loaded


def get_auth_settings_cache() -> AuthSettingsCache:
    """Get the auth settings cache singleton."""
    return AuthSettingsCache()
