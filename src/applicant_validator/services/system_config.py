"""Service for managing system configuration.

This service provides a unified interface for accessing configuration values
that may be stored in various places (integration settings, database, etc.).
"""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database.models import IntegrationSetting

logger = logging.getLogger(__name__)

# Default values for validation settings
VALIDATION_DEFAULTS = {
    "mass_applicant_threshold": 5,
}


class SystemConfigService:
    """Service for accessing system configuration values."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session
        self._cache: dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Configuration value or default.
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        value = None

        # Route to appropriate storage based on key
        if key == "mass_applicant_threshold":
            value = await self._get_lever_config(key)

        # Use default if not found
        if value is None:
            value = default if default is not None else VALIDATION_DEFAULTS.get(key)

        # Cache the value
        if value is not None:
            self._cache[key] = value

        return value

    async def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        # Route to appropriate storage based on key
        if key == "mass_applicant_threshold":
            await self._set_lever_config(key, value)

        # Update cache
        self._cache[key] = value

    async def get_all_validation_settings(self) -> dict[str, Any]:
        """Get all validation-related settings.

        Returns:
            Dictionary of validation settings with their values.
        """
        settings = {}

        # Get mass applicant threshold
        settings["mass_applicant_threshold"] = await self.get(
            "mass_applicant_threshold",
            VALIDATION_DEFAULTS["mass_applicant_threshold"],
        )

        return settings

    async def _get_lever_config(self, key: str) -> Any | None:
        """Get a value from Lever integration config_json.

        Args:
            key: Configuration key.

        Returns:
            Value or None if not found.
        """
        try:
            stmt = select(IntegrationSetting).where(IntegrationSetting.provider == "lever")
            result = await self._session.execute(stmt)
            integration = result.scalar_one_or_none()

            if integration and integration.config_json:
                config = json.loads(integration.config_json)
                return config.get(key)

        except Exception as e:
            logger.debug(f"Error reading Lever config: {e}")

        return None

    async def _set_lever_config(self, key: str, value: Any) -> None:
        """Set a value in Lever integration config_json.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        stmt = select(IntegrationSetting).where(IntegrationSetting.provider == "lever")
        result = await self._session.execute(stmt)
        integration = result.scalar_one_or_none()

        if not integration:
            logger.warning("Lever integration not found, cannot save config")
            return

        # Parse existing config or start with empty dict
        config = {}
        if integration.config_json:
            try:
                config = json.loads(integration.config_json)
            except json.JSONDecodeError:
                config = {}

        # Update the value
        config[key] = value

        # Save back
        integration.config_json = json.dumps(config)
        await self._session.commit()

        logger.info(f"Updated Lever config: {key}={value}")


def get_system_config_service(session: AsyncSession) -> SystemConfigService:
    """Get a system config service instance.

    Args:
        session: SQLAlchemy async session.

    Returns:
        SystemConfigService instance.
    """
    return SystemConfigService(session)
