"""Tests for the integration settings service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from applicant_validator.services.integration_settings import (
    IntegrationSettingsService,
    get_integration_settings_service,
)


class TestIntegrationSettingsService:
    """Tests for IntegrationSettingsService class."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session: AsyncMock) -> IntegrationSettingsService:
        """Create a IntegrationSettingsService instance."""
        return IntegrationSettingsService(mock_session)

    @pytest.fixture
    def mock_integration(self) -> MagicMock:
        """Create a mock integration setting."""
        integration = MagicMock()
        integration.provider = "ipqualityscore"
        integration.display_name = "IPQualityScore"
        integration.is_enabled = True
        integration.api_key = "test_key"  # pragma: allowlist secret
        integration.api_secret = None
        integration.account_id = None
        integration.fraud_score_threshold = 85
        integration.notes = None
        integration.config_json = None
        integration.has_credentials = True
        integration.monthly_usage = 0
        integration.last_test_at = None
        integration.last_test_success = None
        integration.last_test_message = None
        return integration

    @pytest.mark.asyncio
    async def test_get_all_integrations(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should return all integration settings."""
        mock_integration1 = MagicMock()
        mock_integration2 = MagicMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_integration1, mock_integration2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_all_integrations()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_integration(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should return integration for specific provider."""
        mock_integration = MagicMock()
        mock_integration.provider = "ipqualityscore"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_integration("ipqualityscore")

        assert result is not None
        assert result.provider == "ipqualityscore"

    @pytest.mark.asyncio
    async def test_get_integration_not_found(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should return None when integration not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_integration("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_integration_updates_enabled(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should update is_enabled field."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.update_integration("ipqualityscore", is_enabled=False)

        assert result.is_enabled is False

    @pytest.mark.asyncio
    async def test_update_integration_updates_api_key(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should update api_key field."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.update_integration(
            "ipqualityscore",
            api_key="new_key",  # pragma: allowlist secret
        )

        assert result.api_key == "new_key"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_update_integration_clears_api_key(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should clear api_key when empty string provided."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.update_integration("ipqualityscore", api_key="")

        assert result.api_key is None

    @pytest.mark.asyncio
    async def test_update_integration_raises_for_unknown(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should raise ValueError for unknown provider."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await service.update_integration("nonexistent", is_enabled=False)

    @pytest.mark.asyncio
    async def test_update_integration_all_fields(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should update all fields when provided."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        await service.update_integration(
            "ipqualityscore",
            is_enabled=True,
            api_key="new_key",  # pragma: allowlist secret
            api_secret="new_secret",  # pragma: allowlist secret
            account_id="new_account",
            fraud_score_threshold=90,
            notes="Test notes",
            config_json='{"test": true}',
        )

        assert mock_integration.api_key == "new_key"  # pragma: allowlist secret
        assert mock_integration.api_secret == "new_secret"  # pragma: allowlist secret
        assert mock_integration.account_id == "new_account"
        assert mock_integration.fraud_score_threshold == 90
        assert mock_integration.notes == "Test notes"
        assert mock_integration.config_json == '{"test": true}'

    @pytest.mark.asyncio
    async def test_test_integration_provider_not_found(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should return error when provider not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.test_integration("nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_test_integration_no_credentials(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return error when no credentials configured."""
        mock_integration.has_credentials = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.test_integration("ipqualityscore")

        assert result["success"] is False
        assert "credentials" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_test_integration_unknown_provider(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return error for unknown provider type."""
        mock_integration.provider = "unknown_provider"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.test_integration("unknown_provider")

        assert result["success"] is False
        assert "not implemented" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_increment_usage(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should increment monthly usage counter."""
        mock_integration.monthly_usage = 5

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        await service.increment_usage("ipqualityscore")

        assert mock_integration.monthly_usage == 6
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_usage_not_found(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should handle missing integration gracefully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await service.increment_usage("nonexistent")

    @pytest.mark.asyncio
    async def test_reset_monthly_usage(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should reset monthly usage counter."""
        mock_integration.monthly_usage = 100

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        await service.reset_monthly_usage("ipqualityscore")

        assert mock_integration.monthly_usage == 0
        assert mock_integration.usage_reset_at is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_monthly_usage_not_found(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should handle missing integration gracefully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await service.reset_monthly_usage("nonexistent")

    @pytest.mark.asyncio
    async def test_is_enabled_returns_true(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return True when enabled with credentials."""
        mock_integration.is_enabled = True
        mock_integration.has_credentials = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.is_enabled("ipqualityscore")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_enabled_returns_false_when_disabled(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return False when disabled."""
        mock_integration.is_enabled = False
        mock_integration.has_credentials = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.is_enabled("ipqualityscore")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_enabled_returns_false_when_not_found(
        self, service: IntegrationSettingsService, mock_session: AsyncMock
    ) -> None:
        """Should return False when integration not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.is_enabled("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_api_key_returns_key(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return API key when enabled."""
        mock_integration.is_enabled = True
        mock_integration.api_key = "test_api_key"  # pragma: allowlist secret

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_api_key("ipqualityscore")

        assert result == "test_api_key"

    @pytest.mark.asyncio
    async def test_get_api_key_returns_none_when_disabled(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return None when disabled."""
        mock_integration.is_enabled = False
        mock_integration.api_key = "test_api_key"  # pragma: allowlist secret

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_api_key("ipqualityscore")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_credentials_returns_all(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return all credentials."""
        mock_integration.is_enabled = True
        mock_integration.api_key = "test_key"  # pragma: allowlist secret
        mock_integration.api_secret = "test_secret"  # pragma: allowlist secret
        mock_integration.account_id = "test_account"
        mock_integration.fraud_score_threshold = 85

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_credentials("ipqualityscore")

        assert result is not None
        assert result["api_key"] == "test_key"  # pragma: allowlist secret
        assert result["api_secret"] == "test_secret"  # pragma: allowlist secret
        assert result["account_id"] == "test_account"
        assert result["fraud_score_threshold"] == 85

    @pytest.mark.asyncio
    async def test_get_credentials_returns_none_when_disabled(
        self,
        service: IntegrationSettingsService,
        mock_session: AsyncMock,
        mock_integration: MagicMock,
    ) -> None:
        """Should return None when disabled."""
        mock_integration.is_enabled = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_integration
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_credentials("ipqualityscore")

        assert result is None


class TestGetIntegrationSettingsService:
    """Tests for get_integration_settings_service function."""

    @pytest.mark.asyncio
    async def test_returns_service_instance(self) -> None:
        """Should return IntegrationSettingsService instance."""
        mock_session = AsyncMock()

        result = await get_integration_settings_service(mock_session)

        assert isinstance(result, IntegrationSettingsService)
