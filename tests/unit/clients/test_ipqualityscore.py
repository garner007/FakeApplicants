"""Tests for the IPQualityScore client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from applicant_validator.clients.ipqualityscore import (
    IPQS_BASE_URL,
    IPQualityScoreClient,
    PhoneValidationResult,
    get_ipqs_client,
    validate_phone_with_ipqs,
)


class TestPhoneValidationResult:
    """Tests for PhoneValidationResult dataclass."""

    def test_from_api_response_full_data(self) -> None:
        """Should parse complete API response."""
        data = {
            "valid": True,
            "fraud_score": 25,
            "VOIP": False,
            "line_type": "wireless",
            "carrier": "Verizon",
            "active": True,
            "active_status": "active",
            "prepaid": False,
            "risky": False,
            "recent_abuse": False,
            "country": "US",
            "region": "California",
            "city": "San Francisco",
            "timezone": "America/Los_Angeles",
            "formatted": "+1-555-123-4567",
            "local_format": "(555) 123-4567",
        }

        result = PhoneValidationResult.from_api_response(data)

        assert result.valid is True
        assert result.fraud_score == 25
        assert result.is_voip is False
        assert result.line_type == "wireless"
        assert result.carrier == "Verizon"
        assert result.active is True
        assert result.country == "US"

    def test_from_api_response_minimal_data(self) -> None:
        """Should handle minimal API response with defaults."""
        data = {}

        result = PhoneValidationResult.from_api_response(data)

        assert result.valid is False
        assert result.fraud_score == 0
        assert result.is_voip is False
        assert result.active is False
        assert result.prepaid is False
        assert result.risky is False
        assert result.recent_abuse is False

    def test_is_high_risk_high_fraud_score(self) -> None:
        """Should identify high fraud score as high risk."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=90,
            is_voip=False,
            line_type="wireless",
            carrier="AT&T",
            active=True,
            active_status="active",
            prepaid=False,
            risky=False,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        assert result.is_high_risk is True

    def test_is_high_risk_risky_flag(self) -> None:
        """Should identify risky flag as high risk."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=50,
            is_voip=False,
            line_type="wireless",
            carrier="AT&T",
            active=True,
            active_status="active",
            prepaid=False,
            risky=True,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        assert result.is_high_risk is True

    def test_is_high_risk_recent_abuse(self) -> None:
        """Should identify recent abuse as high risk."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=50,
            is_voip=False,
            line_type="wireless",
            carrier="AT&T",
            active=True,
            active_status="active",
            prepaid=False,
            risky=False,
            recent_abuse=True,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        assert result.is_high_risk is True

    def test_is_high_risk_low_score(self) -> None:
        """Should not identify low fraud score as high risk."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=20,
            is_voip=False,
            line_type="wireless",
            carrier="AT&T",
            active=True,
            active_status="active",
            prepaid=False,
            risky=False,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        assert result.is_high_risk is False

    def test_risk_factors_voip(self) -> None:
        """Should include VoIP in risk factors."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=20,
            is_voip=True,
            line_type="VoIP",
            carrier="Twilio",
            active=True,
            active_status="active",
            prepaid=False,
            risky=False,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        factors = result.risk_factors
        assert "VoIP number" in factors

    def test_risk_factors_prepaid(self) -> None:
        """Should include prepaid in risk factors."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=20,
            is_voip=False,
            line_type="wireless",
            carrier="TracFone",
            active=True,
            active_status="active",
            prepaid=True,
            risky=False,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        factors = result.risk_factors
        assert "Prepaid line" in factors

    def test_risk_factors_inactive(self) -> None:
        """Should include inactive in risk factors."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=20,
            is_voip=False,
            line_type="wireless",
            carrier="AT&T",
            active=False,
            active_status="inactive",
            prepaid=False,
            risky=False,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        factors = result.risk_factors
        assert "Inactive line" in factors

    def test_risk_factors_elevated_score(self) -> None:
        """Should include elevated fraud score in risk factors."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=80,
            is_voip=False,
            line_type="wireless",
            carrier="AT&T",
            active=True,
            active_status="active",
            prepaid=False,
            risky=False,
            recent_abuse=False,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        factors = result.risk_factors
        assert any("Elevated fraud score" in f for f in factors)

    def test_risk_factors_multiple(self) -> None:
        """Should include multiple risk factors."""
        result = PhoneValidationResult(
            valid=True,
            fraud_score=90,
            is_voip=True,
            line_type="VoIP",
            carrier="Unknown",
            active=False,
            active_status="inactive",
            prepaid=True,
            risky=True,
            recent_abuse=True,
            country="US",
            region=None,
            city=None,
            timezone=None,
            formatted=None,
            local_format=None,
            raw_response={},
        )

        factors = result.risk_factors
        assert len(factors) >= 4


class TestIPQualityScoreClient:
    """Tests for IPQualityScoreClient."""

    def test_init(self) -> None:
        """Should initialize with API key."""
        client = IPQualityScoreClient(api_key="test_api_key")  # pragma: allowlist secret
        assert client._api_key == "test_api_key"  # pragma: allowlist secret
        assert client.service_name == "IPQualityScore"

    def test_service_name(self) -> None:
        """Should return correct service name."""
        client = IPQualityScoreClient(api_key="test_key")
        assert client.service_name == "IPQualityScore"

    @pytest.mark.asyncio
    @respx.mock
    async def test_validate_phone_success(self) -> None:
        """Should validate phone number successfully."""
        api_response = {
            "success": True,
            "valid": True,
            "fraud_score": 15,
            "VOIP": False,
            "line_type": "wireless",
            "carrier": "Verizon",
            "active": True,
            "country": "US",
        }

        respx.get(f"{IPQS_BASE_URL}/phone/test_key/+15551234567").mock(
            return_value=Response(200, json=api_response)
        )

        client = IPQualityScoreClient(api_key="test_key")
        result = await client.validate_phone("+15551234567")

        assert result.valid is True
        assert result.fraud_score == 15
        assert result.is_voip is False
        assert result.carrier == "Verizon"

    @pytest.mark.asyncio
    @respx.mock
    async def test_validate_phone_with_country(self) -> None:
        """Should pass country parameter to API."""
        api_response = {
            "success": True,
            "valid": True,
            "fraud_score": 10,
        }

        route = respx.get(f"{IPQS_BASE_URL}/phone/test_key/5551234567").mock(
            return_value=Response(200, json=api_response)
        )

        client = IPQualityScoreClient(api_key="test_key")
        await client.validate_phone("5551234567", country="US")

        assert route.called
        assert "country=US" in str(route.calls[0].request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_validate_phone_with_country_list(self) -> None:
        """Should pass multiple countries to API."""
        api_response = {
            "success": True,
            "valid": True,
            "fraud_score": 10,
        }

        respx.get(f"{IPQS_BASE_URL}/phone/test_key/5551234567").mock(
            return_value=Response(200, json=api_response)
        )

        client = IPQualityScoreClient(api_key="test_key")
        result = await client.validate_phone("5551234567", country=["US", "CA"])

        assert result.valid is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_validate_phone_api_error(self) -> None:
        """Should return default result on API error."""
        api_response = {
            "success": False,
            "message": "Invalid phone number format",
        }

        respx.get(f"{IPQS_BASE_URL}/phone/test_key/invalid").mock(
            return_value=Response(200, json=api_response)
        )

        client = IPQualityScoreClient(api_key="test_key")
        result = await client.validate_phone("invalid")

        assert result.valid is False
        assert result.fraud_score == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_check_voip(self) -> None:
        """Should return VoIP status and details."""
        api_response = {
            "success": True,
            "valid": True,
            "fraud_score": 50,
            "VOIP": True,
            "carrier": "Twilio",
            "line_type": "VoIP",
            "active": True,
        }

        respx.get(f"{IPQS_BASE_URL}/phone/test_key/+15551234567").mock(
            return_value=Response(200, json=api_response)
        )

        client = IPQualityScoreClient(api_key="test_key")
        is_voip, details = await client.check_voip("+15551234567")

        assert is_voip is True
        assert details["carrier"] == "Twilio"
        assert details["line_type"] == "VoIP"


class TestGetIPQSClient:
    """Tests for get_ipqs_client function."""

    def test_returns_none_when_disabled(self) -> None:
        """Should return None when IPQS is disabled."""
        # Clear cached client
        import applicant_validator.clients.ipqualityscore as ipqs_module

        ipqs_module._client = None
        ipqs_module._client_source = None

        with patch("applicant_validator.config.get_settings") as mock_settings:
            mock_settings.return_value.ipqualityscore_enabled = False

            result = get_ipqs_client()

            assert result is None

    def test_returns_none_when_no_credentials(self) -> None:
        """Should return None when credentials not configured."""
        # Clear cached client
        import applicant_validator.clients.ipqualityscore as ipqs_module

        ipqs_module._client = None
        ipqs_module._client_source = None

        with patch("applicant_validator.config.get_settings") as mock_settings:
            mock_settings.return_value.ipqualityscore_enabled = True
            mock_settings.return_value.has_ipqualityscore_credentials = False

            result = get_ipqs_client()

            assert result is None


class TestValidatePhoneWithIPQS:
    """Tests for validate_phone_with_ipqs function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self) -> None:
        """Should return None when IPQS not configured."""
        # Clear cached client
        import applicant_validator.clients.ipqualityscore as ipqs_module

        ipqs_module._client = None
        ipqs_module._client_source = None

        with (
            patch(
                "applicant_validator.clients.ipqualityscore._get_ipqs_client_from_db",
                return_value=None,
            ),
            patch(
                "applicant_validator.clients.ipqualityscore.get_ipqs_client",
                return_value=None,
            ),
        ):
            result = await validate_phone_with_ipqs("+15551234567")

            assert result is None

    @pytest.mark.asyncio
    async def test_uses_cached_client(self) -> None:
        """Should use cached client when available."""
        import applicant_validator.clients.ipqualityscore as ipqs_module

        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_client.validate_phone.return_value = mock_result
        ipqs_module._client = mock_client
        ipqs_module._client_source = "test"

        result = await validate_phone_with_ipqs("+15551234567")

        assert result == mock_result
        mock_client.validate_phone.assert_called_once_with("+15551234567")

        # Reset
        ipqs_module._client = None
        ipqs_module._client_source = None

    @pytest.mark.asyncio
    async def test_handles_validation_error(self) -> None:
        """Should return None on validation error."""
        import applicant_validator.clients.ipqualityscore as ipqs_module

        mock_client = AsyncMock()
        mock_client.validate_phone.side_effect = Exception("API Error")
        ipqs_module._client = mock_client
        ipqs_module._client_source = "test"

        result = await validate_phone_with_ipqs("+15551234567")

        assert result is None

        # Reset
        ipqs_module._client = None
        ipqs_module._client_source = None
