"""Tests for the system config service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from applicant_validator.services.system_config import (
    VALIDATION_DEFAULTS,
    SystemConfigService,
    get_system_config_service,
)


class TestValidationDefaults:
    """Tests for VALIDATION_DEFAULTS constant."""

    def test_has_mass_applicant_threshold(self) -> None:
        """Should have mass_applicant_threshold default."""
        assert "mass_applicant_threshold" in VALIDATION_DEFAULTS
        assert isinstance(VALIDATION_DEFAULTS["mass_applicant_threshold"], int)


class TestSystemConfigService:
    """Tests for SystemConfigService class."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session: AsyncMock) -> SystemConfigService:
        """Create a SystemConfigService instance."""
        return SystemConfigService(mock_session)

    @pytest.mark.asyncio
    async def test_get_returns_cached_value(self, service: SystemConfigService) -> None:
        """Should return cached value if available."""
        service._cache["test_key"] = "cached_value"

        result = await service.get("test_key")

        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_get_mass_applicant_threshold_from_db(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should get mass_applicant_threshold from Lever integration."""
        mock_integration = MagicMock()
        mock_integration.config_json = json.dumps({"mass_applicant_threshold": 10})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get("mass_applicant_threshold")

        assert result == 10

    @pytest.mark.asyncio
    async def test_get_uses_default_when_not_in_db(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should use default value when not found in database."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get("mass_applicant_threshold")

        assert result == VALIDATION_DEFAULTS["mass_applicant_threshold"]

    @pytest.mark.asyncio
    async def test_get_uses_provided_default(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should use provided default value."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get("unknown_key", default="custom_default")

        assert result == "custom_default"

    @pytest.mark.asyncio
    async def test_get_caches_value(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should cache retrieved value."""
        mock_integration = MagicMock()
        mock_integration.config_json = json.dumps({"mass_applicant_threshold": 7})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        await service.get("mass_applicant_threshold")

        assert "mass_applicant_threshold" in service._cache

    @pytest.mark.asyncio
    async def test_set_updates_lever_config(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should update value in Lever integration config."""
        mock_integration = MagicMock()
        mock_integration.config_json = json.dumps({})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        await service.set("mass_applicant_threshold", 15)

        # Should have updated config_json
        config = json.loads(mock_integration.config_json)
        assert config["mass_applicant_threshold"] == 15

    @pytest.mark.asyncio
    async def test_set_creates_new_config(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should create config when none exists."""
        mock_integration = MagicMock()
        mock_integration.config_json = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        await service.set("mass_applicant_threshold", 8)

        config = json.loads(mock_integration.config_json)
        assert config["mass_applicant_threshold"] == 8

    @pytest.mark.asyncio
    async def test_set_handles_invalid_json(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should handle invalid JSON in existing config."""
        mock_integration = MagicMock()
        mock_integration.config_json = "invalid json"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        await service.set("mass_applicant_threshold", 12)

        config = json.loads(mock_integration.config_json)
        assert config["mass_applicant_threshold"] == 12

    @pytest.mark.asyncio
    async def test_set_handles_missing_integration(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should handle case when Lever integration doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise, just log warning
        await service.set("mass_applicant_threshold", 20)

    @pytest.mark.asyncio
    async def test_set_updates_cache(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should update cache after setting value."""
        mock_integration = MagicMock()
        mock_integration.config_json = json.dumps({})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        await service.set("mass_applicant_threshold", 25)

        assert service._cache["mass_applicant_threshold"] == 25

    @pytest.mark.asyncio
    async def test_get_all_validation_settings(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should return all validation settings."""
        mock_integration = MagicMock()
        mock_integration.config_json = json.dumps({"mass_applicant_threshold": 10})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_all_validation_settings()

        assert "mass_applicant_threshold" in result
        assert result["mass_applicant_threshold"] == 10

    @pytest.mark.asyncio
    async def test_get_lever_config_handles_exception(
        self, service: SystemConfigService, mock_session: AsyncMock
    ) -> None:
        """Should handle exceptions when reading Lever config."""
        mock_session.execute = AsyncMock(side_effect=Exception("DB Error"))

        result = await service._get_lever_config("test_key")

        assert result is None


class TestGetSystemConfigService:
    """Tests for get_system_config_service function."""

    def test_returns_service_instance(self) -> None:
        """Should return SystemConfigService instance."""
        mock_session = AsyncMock()

        result = get_system_config_service(mock_session)

        assert isinstance(result, SystemConfigService)
