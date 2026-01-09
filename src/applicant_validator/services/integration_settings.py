"""Service for managing integration settings."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database.models import IntegrationProvider, IntegrationSetting

logger = logging.getLogger(__name__)


class IntegrationSettingsService:
    """Service for managing API integration settings."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    async def get_all_integrations(self) -> list[IntegrationSetting]:
        """Get all integration settings.

        Returns:
            List of all integration settings.
        """
        stmt = select(IntegrationSetting).order_by(IntegrationSetting.display_name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_integration(self, provider: str) -> IntegrationSetting | None:
        """Get integration settings for a specific provider.

        Args:
            provider: Provider name (e.g., 'ipqualityscore', 'twilio').

        Returns:
            IntegrationSetting or None if not found.
        """
        stmt = select(IntegrationSetting).where(IntegrationSetting.provider == provider.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_integration(
        self,
        provider: str,
        *,
        is_enabled: bool | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        account_id: str | None = None,
        fraud_score_threshold: int | None = None,
        notes: str | None = None,
    ) -> IntegrationSetting:
        """Update integration settings.

        Args:
            provider: Provider name.
            is_enabled: Enable/disable the integration.
            api_key: API key (pass empty string to clear).
            api_secret: API secret (pass empty string to clear).
            account_id: Account ID (pass empty string to clear).
            fraud_score_threshold: Fraud score threshold (for IPQS).
            notes: Notes about this integration.

        Returns:
            Updated IntegrationSetting.

        Raises:
            ValueError: If provider not found.
        """
        integration = await self.get_integration(provider)
        if not integration:
            raise ValueError(f"Integration provider '{provider}' not found")

        # Update fields if provided
        if is_enabled is not None:
            integration.is_enabled = is_enabled

        if api_key is not None:
            integration.api_key = api_key if api_key else None

        if api_secret is not None:
            integration.api_secret = api_secret if api_secret else None

        if account_id is not None:
            integration.account_id = account_id if account_id else None

        if fraud_score_threshold is not None:
            integration.fraud_score_threshold = fraud_score_threshold

        if notes is not None:
            integration.notes = notes if notes else None

        await self._session.commit()
        await self._session.refresh(integration)

        logger.info(f"Updated integration settings for {provider}")
        return integration

    async def test_integration(self, provider: str) -> dict[str, Any]:
        """Test an integration by making a simple API call.

        Args:
            provider: Provider name.

        Returns:
            Dict with 'success', 'message', and optional 'details'.
        """
        integration = await self.get_integration(provider)
        if not integration:
            return {"success": False, "message": f"Provider '{provider}' not found"}

        if not integration.has_credentials:
            return {"success": False, "message": "No credentials configured"}

        result: dict[str, Any] = {"success": False, "message": "Unknown error"}

        try:
            if provider == IntegrationProvider.IPQUALITYSCORE.value:
                result = await self._test_ipqualityscore(integration)
            elif provider == IntegrationProvider.TWILIO.value:
                result = await self._test_twilio(integration)
            else:
                result = {"success": False, "message": f"Testing not implemented for {provider}"}

        except Exception as e:
            logger.exception(f"Error testing {provider} integration")
            result = {"success": False, "message": str(e)}

        # Update test status
        integration.last_test_at = datetime.now(UTC)
        integration.last_test_success = result["success"]
        integration.last_test_message = result["message"][:500] if result["message"] else None
        await self._session.commit()

        return result

    async def _test_ipqualityscore(self, integration: IntegrationSetting) -> dict[str, Any]:
        """Test IPQualityScore integration.

        Args:
            integration: Integration settings.

        Returns:
            Test result dict.
        """
        import httpx

        if not integration.api_key:
            return {"success": False, "message": "API key not configured"}

        # Test with a known valid phone number format
        test_phone = "+12025551234"  # DC area test number
        url = f"https://www.ipqualityscore.com/api/json/phone/{integration.api_key}/{test_phone}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

            if data.get("success") is False:
                message = data.get("message", "API request failed")
                return {"success": False, "message": message}

            # Check if we got valid response fields
            if "valid" in data or "fraud_score" in data:
                return {
                    "success": True,
                    "message": "API connection successful",
                    "details": {
                        "fraud_score": data.get("fraud_score"),
                        "valid": data.get("valid"),
                    },
                }

            return {"success": False, "message": "Unexpected API response format"}

    async def _test_twilio(self, integration: IntegrationSetting) -> dict[str, Any]:
        """Test Twilio integration.

        Args:
            integration: Integration settings.

        Returns:
            Test result dict.
        """
        if not integration.account_id or not integration.api_secret:
            return {
                "success": False,
                "message": "Account SID and Auth Token required",
            }

        try:
            from twilio.rest import Client  # type: ignore[import-not-found]

            client = Client(integration.account_id, integration.api_secret)

            # Try to fetch account info to verify credentials
            account = client.api.accounts(integration.account_id).fetch()

            return {
                "success": True,
                "message": "API connection successful",
                "details": {
                    "account_name": account.friendly_name,
                    "status": account.status,
                },
            }
        except ImportError:
            return {
                "success": False,
                "message": "Twilio library not installed. Run: pip install twilio",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def increment_usage(self, provider: str) -> None:
        """Increment the monthly usage counter for a provider.

        Args:
            provider: Provider name.
        """
        integration = await self.get_integration(provider)
        if integration:
            integration.monthly_usage += 1
            await self._session.commit()

    async def reset_monthly_usage(self, provider: str) -> None:
        """Reset the monthly usage counter for a provider.

        Args:
            provider: Provider name.
        """
        integration = await self.get_integration(provider)
        if integration:
            integration.monthly_usage = 0
            integration.usage_reset_at = datetime.now(UTC)
            await self._session.commit()

    async def is_enabled(self, provider: str) -> bool:
        """Check if an integration is enabled.

        Args:
            provider: Provider name.

        Returns:
            True if enabled and has credentials.
        """
        integration = await self.get_integration(provider)
        if not integration:
            return False
        return integration.is_enabled and integration.has_credentials

    async def get_api_key(self, provider: str) -> str | None:
        """Get the API key for a provider.

        Args:
            provider: Provider name.

        Returns:
            API key or None.
        """
        integration = await self.get_integration(provider)
        if integration and integration.is_enabled:
            return integration.api_key
        return None

    async def get_credentials(self, provider: str) -> dict[str, Any] | None:
        """Get all credentials for a provider.

        Args:
            provider: Provider name.

        Returns:
            Dict with api_key, api_secret, account_id, or None if not enabled.
        """
        integration = await self.get_integration(provider)
        if not integration or not integration.is_enabled:
            return None

        return {
            "api_key": integration.api_key,
            "api_secret": integration.api_secret,
            "account_id": integration.account_id,
            "fraud_score_threshold": integration.fraud_score_threshold,
        }


# Singleton service instance (requires session injection)
_service: IntegrationSettingsService | None = None


async def get_integration_settings_service(
    session: AsyncSession,
) -> IntegrationSettingsService:
    """Get the integration settings service.

    Args:
        session: SQLAlchemy async session.

    Returns:
        IntegrationSettingsService instance.
    """
    return IntegrationSettingsService(session)
