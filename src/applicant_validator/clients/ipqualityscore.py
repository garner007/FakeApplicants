"""IPQualityScore API client for phone number validation."""

import logging
from dataclasses import dataclass
from typing import Any

from applicant_validator.clients.base import BaseClient, RetryConfig

logger = logging.getLogger(__name__)

IPQS_BASE_URL = "https://www.ipqualityscore.com/api/json"


@dataclass
class PhoneValidationResult:
    """Result from IPQualityScore phone validation."""

    valid: bool
    fraud_score: int
    is_voip: bool
    line_type: str | None
    carrier: str | None
    active: bool
    active_status: str | None
    prepaid: bool
    risky: bool
    recent_abuse: bool
    country: str | None
    region: str | None
    city: str | None
    timezone: str | None
    formatted: str | None
    local_format: str | None
    raw_response: dict[str, Any]

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PhoneValidationResult":
        """Create PhoneValidationResult from API response.

        Args:
            data: Raw API response dictionary.

        Returns:
            PhoneValidationResult instance.
        """
        return cls(
            valid=data.get("valid", False),
            fraud_score=data.get("fraud_score", 0),
            is_voip=data.get("VOIP", False),
            line_type=data.get("line_type"),
            carrier=data.get("carrier"),
            active=data.get("active", False),
            active_status=data.get("active_status"),
            prepaid=data.get("prepaid", False),
            risky=data.get("risky", False),
            recent_abuse=data.get("recent_abuse", False),
            country=data.get("country"),
            region=data.get("region"),
            city=data.get("city"),
            timezone=data.get("timezone"),
            formatted=data.get("formatted"),
            local_format=data.get("local_format"),
            raw_response=data,
        )

    @property
    def is_high_risk(self) -> bool:
        """Check if the phone number is considered high risk."""
        return self.fraud_score >= 85 or self.risky or self.recent_abuse

    @property
    def risk_factors(self) -> list[str]:
        """Get list of risk factors for this phone number."""
        factors = []
        if self.is_voip:
            factors.append("VoIP number")
        if self.prepaid:
            factors.append("Prepaid line")
        if self.recent_abuse:
            factors.append("Recent abuse reported")
        if self.risky:
            factors.append("Flagged as risky")
        if not self.active:
            factors.append("Inactive line")
        if self.fraud_score >= 85:
            factors.append(f"High fraud score ({self.fraud_score})")
        elif self.fraud_score >= 75:
            factors.append(f"Elevated fraud score ({self.fraud_score})")
        return factors


class IPQualityScoreClient(BaseClient):
    """Client for IPQualityScore Phone Validation API.

    IPQualityScore provides phone number validation with:
    - VoIP detection
    - Fraud scoring (0-100)
    - Carrier identification
    - Line type detection (wireless, landline, VoIP, prepaid)
    - Active/inactive status
    - Abuse history

    Free tier: 1,000 lookups per month.
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize the IPQualityScore client.

        Args:
            api_key: IPQualityScore API key.
            timeout: Request timeout in seconds.
            retry_config: Configuration for retry behavior.
        """
        super().__init__(
            base_url=IPQS_BASE_URL,
            timeout=timeout,
            retry_config=retry_config,
        )
        self._api_key = api_key

    @property
    def service_name(self) -> str:
        """Get the service name for error messages."""
        return "IPQualityScore"

    async def validate_phone(
        self,
        phone_number: str,
        country: str | list[str] | None = None,
        strictness: int = 0,
    ) -> PhoneValidationResult:
        """Validate a phone number using IPQualityScore API.

        Args:
            phone_number: Phone number to validate (E.164 format preferred).
            country: Country code(s) to help with parsing. Can be single code
                     like "US" or list like ["US", "CA"].
            strictness: Strictness level 0-2. Higher = more strict scoring.
                       0 = recommended for most use cases.

        Returns:
            PhoneValidationResult with validation details.

        Raises:
            httpx.HTTPStatusError: If API request fails.
        """
        # Build the path with API key and phone number
        # IPQualityScore expects: /phone/{api_key}/{phone_number}
        path = f"/phone/{self._api_key}/{phone_number}"

        # Build query parameters
        params: dict[str, Any] = {
            "strictness": strictness,
        }

        # Handle country parameter
        if country:
            if isinstance(country, list):
                # Multiple countries - add each as separate param
                # The API accepts multiple country params
                params["country[]"] = country
            else:
                params["country"] = country

        logger.debug(f"Validating phone number with IPQS: {phone_number[:6]}***")

        try:
            response = await self.get(path, params=params)

            # Check for API-level errors
            if not response.get("success", True):
                error_message = response.get("message", "Unknown error")
                logger.warning(f"IPQS API error: {error_message}")
                # Return a default "unknown" result on API error
                return PhoneValidationResult(
                    valid=False,
                    fraud_score=0,
                    is_voip=False,
                    line_type=None,
                    carrier=None,
                    active=False,
                    active_status=None,
                    prepaid=False,
                    risky=False,
                    recent_abuse=False,
                    country=None,
                    region=None,
                    city=None,
                    timezone=None,
                    formatted=None,
                    local_format=None,
                    raw_response=response,
                )

            result = PhoneValidationResult.from_api_response(response)
            logger.info(
                f"IPQS validation complete: valid={result.valid}, "
                f"voip={result.is_voip}, fraud_score={result.fraud_score}, "
                f"carrier={result.carrier}"
            )
            return result

        except Exception as e:
            logger.error(f"IPQS phone validation failed: {e}")
            raise

    async def check_voip(self, phone_number: str) -> tuple[bool, dict[str, Any]]:
        """Simple check if a phone number is VoIP.

        Convenience method that returns just the VoIP status and details.

        Args:
            phone_number: Phone number to check.

        Returns:
            Tuple of (is_voip, details_dict).
        """
        result = await self.validate_phone(phone_number)

        details = {
            "is_voip": result.is_voip,
            "fraud_score": result.fraud_score,
            "carrier": result.carrier,
            "line_type": result.line_type,
            "active": result.active,
            "risk_factors": result.risk_factors,
        }

        return result.is_voip, details


# Module-level client instances (lazy initialization)
_client: IPQualityScoreClient | None = None
_client_source: str | None = None  # Track where credentials came from


async def _get_ipqs_client_from_db() -> IPQualityScoreClient | None:
    """Try to get IPQualityScore client from database settings.

    Returns:
        IPQualityScoreClient if configured in database, None otherwise.
    """
    try:
        from applicant_validator.database.base import get_session
        from applicant_validator.services.integration_settings import (
            get_integration_settings_service,
        )

        async for session in get_session():
            service = await get_integration_settings_service(session)
            credentials = await service.get_credentials("ipqualityscore")

            if credentials and credentials.get("api_key"):
                client = IPQualityScoreClient(api_key=credentials["api_key"])
                logger.info("IPQualityScore client initialized from database settings")
                return client

    except Exception as e:
        logger.debug(f"Could not get IPQS from database: {e}")

    return None


def get_ipqs_client() -> IPQualityScoreClient | None:
    """Get the IPQualityScore client singleton from environment variables.

    NOTE: Prefer using validate_phone_with_ipqs() which checks database first.

    Returns:
        IPQualityScoreClient if configured via env vars, None otherwise.
    """
    global _client, _client_source  # noqa: PLW0603

    if _client is not None:
        return _client

    try:
        from applicant_validator.config import get_settings

        settings = get_settings()

        if not settings.ipqualityscore_enabled:
            logger.debug("IPQualityScore is not enabled via environment")
            return None

        if not settings.has_ipqualityscore_credentials:
            logger.warning("IPQualityScore enabled but no API key configured in environment")
            return None

        _client = IPQualityScoreClient(api_key=settings.ipqualityscore_api_key)
        _client_source = "environment"
        logger.info("IPQualityScore client initialized from environment variables")
        return _client

    except Exception as e:
        logger.warning(f"Could not initialize IPQualityScore client: {e}")
        return None


async def validate_phone_with_ipqs(  # noqa: PLR0911
    phone_number: str,
) -> PhoneValidationResult | None:
    """Validate a phone number using IPQualityScore if configured.

    Checks database settings first, falls back to environment variables.

    Args:
        phone_number: Phone number to validate.

    Returns:
        PhoneValidationResult if IPQS is configured and lookup succeeds,
        None otherwise.
    """
    global _client, _client_source  # noqa: PLW0603

    # Try to use cached client first
    if _client is not None:
        try:
            return await _client.validate_phone(phone_number)
        except Exception as e:
            logger.warning(f"IPQS phone validation failed: {e}")
            return None

    # Try database settings first
    db_client = await _get_ipqs_client_from_db()
    if db_client is not None:
        _client = db_client
        _client_source = "database"
        try:
            return await db_client.validate_phone(phone_number)
        except Exception as e:
            logger.warning(f"IPQS phone validation failed: {e}")
            return None

    # Fall back to environment variables
    env_client = get_ipqs_client()
    if env_client is None:
        return None

    try:
        return await env_client.validate_phone(phone_number)
    except Exception as e:
        logger.warning(f"IPQS phone validation failed: {e}")
        return None
