"""Tests for LeverClient."""

import base64

import httpx
import pytest
import respx

from applicant_validator.clients.lever import LeverClient
from applicant_validator.exceptions import ApplicantNotFoundError, LeverAPIError


class TestLeverClientInit:
    """Tests for LeverClient initialization."""

    def test_creation_with_api_key(self) -> None:
        """LeverClient should be creatable with API key."""
        client = LeverClient(
            api_key="test_api_key"  # pragma: allowlist secret
        )
        assert client.api_key == "test_api_key"  # pragma: allowlist secret
        assert client.service_name == "Lever"

    def test_default_sandbox_environment(self) -> None:
        """LeverClient should default to sandbox environment."""
        client = LeverClient(api_key="test_api_key")  # pragma: allowlist secret
        assert client.environment == "sandbox"
        assert "sandbox" in client.base_url

    def test_production_environment(self) -> None:
        """LeverClient should support production environment."""
        client = LeverClient(api_key="test_api_key", environment="production")
        assert client.environment == "production"
        assert "sandbox" not in client.base_url
        assert client.base_url == "https://api.lever.co/v1"

    def test_sandbox_base_url(self) -> None:
        """LeverClient should use correct sandbox URL."""
        client = LeverClient(api_key="test_api_key", environment="sandbox")
        assert client.base_url == "https://api.sandbox.lever.co/v1"

    def test_basic_auth_header(self) -> None:
        """LeverClient should set up Basic Auth correctly."""
        client = LeverClient(api_key="my_secret_key")
        headers = client._get_default_headers()

        # Basic auth should be base64(api_key:)
        expected_auth = base64.b64encode(b"my_secret_key:").decode()
        assert headers["Authorization"] == f"Basic {expected_auth}"


class TestLeverClientGetApplicants:
    """Tests for LeverClient.get_applicants()."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applicants_success(self) -> None:
        """Should return list of applicants."""
        mock_response = {
            "data": [
                {
                    "id": "abc123",
                    "name": "John Doe",
                    "emails": ["john@example.com"],
                    "phones": [{"value": "+1-555-1234"}],
                    "links": ["https://linkedin.com/in/johndoe"],
                    "location": "San Francisco",
                    "headline": "Software Engineer",
                    "sources": ["LinkedIn"],
                    "createdAt": 1704067200000,
                    "opportunityIds": ["opp123"],
                    "stageChanges": [{"toStageId": "stage1"}],
                },
                {
                    "id": "def456",
                    "name": "Jane Smith",
                    "emails": ["jane@example.com"],
                    "phones": [],
                    "links": [],
                    "location": None,
                    "headline": None,
                    "sources": ["Referral"],
                    "createdAt": 1704153600000,
                    "opportunityIds": ["opp456"],
                    "stageChanges": [{"toStageId": "stage2"}],
                },
            ],
            "hasNext": False,
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicants = await client.get_applicants()

        assert len(applicants) == 2
        assert applicants[0].id == "abc123"
        assert applicants[0].name == "John Doe"
        assert applicants[0].email == "john@example.com"
        assert applicants[1].id == "def456"
        assert applicants[1].name == "Jane Smith"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applicants_with_limit(self) -> None:
        """Should pass limit parameter to API."""
        route = respx.get("https://api.sandbox.lever.co/v1/candidates").mock(
            return_value=httpx.Response(200, json={"data": [], "hasNext": False})
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            await client.get_applicants(limit=10)

        assert "limit=10" in str(route.calls.last.request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applicants_with_offset(self) -> None:
        """Should pass offset parameter to API."""
        route = respx.get("https://api.sandbox.lever.co/v1/candidates").mock(
            return_value=httpx.Response(200, json={"data": [], "hasNext": False})
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            await client.get_applicants(offset="cursor123")

        assert "offset=cursor123" in str(route.calls.last.request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applicants_empty_list(self) -> None:
        """Should handle empty applicant list."""
        respx.get("https://api.sandbox.lever.co/v1/candidates").mock(
            return_value=httpx.Response(200, json={"data": [], "hasNext": False})
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicants = await client.get_applicants()

        assert applicants == []


class TestLeverClientGetApplicant:
    """Tests for LeverClient.get_applicant()."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applicant_success(self) -> None:
        """Should return single applicant by ID."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [{"value": "+1-555-1234"}],
                "links": ["https://linkedin.com/in/johndoe"],
                "location": "San Francisco",
                "headline": "Software Engineer",
                "sources": ["LinkedIn"],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.id == "abc123"
        assert applicant.name == "John Doe"
        assert applicant.email == "john@example.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_applicant_not_found(self) -> None:
        """Should raise ApplicantNotFoundError for 404."""
        respx.get("https://api.sandbox.lever.co/v1/candidates/nonexistent").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            with pytest.raises(ApplicantNotFoundError) as exc_info:
                await client.get_applicant("nonexistent")

        assert exc_info.value.applicant_id == "nonexistent"


class TestLeverClientGetOpportunities:
    """Tests for LeverClient.get_opportunities()."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_opportunities_success(self) -> None:
        """Should return list of opportunities."""
        mock_response = {
            "data": [
                {
                    "id": "opp123",
                    "name": "Software Engineer",
                    "headline": "Join our team",
                    "stage": {"id": "stage1", "text": "Application Review"},
                },
                {
                    "id": "opp456",
                    "name": "Product Manager",
                    "headline": "Lead products",
                    "stage": {"id": "stage2", "text": "Interview"},
                },
            ],
            "hasNext": False,
        }

        respx.get("https://api.sandbox.lever.co/v1/opportunities").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            opportunities = await client.get_opportunities()

        assert len(opportunities) == 2
        assert opportunities[0]["id"] == "opp123"
        assert opportunities[1]["id"] == "opp456"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_opportunities_for_candidate(self) -> None:
        """Should get opportunities for specific candidate."""
        mock_response = {
            "data": [
                {
                    "id": "opp789",
                    "name": "DevOps Engineer",
                    "headline": "Build infrastructure",
                    "stage": {"id": "stage3", "text": "Offer"},
                },
            ],
            "hasNext": False,
        }

        route = respx.get("https://api.sandbox.lever.co/v1/opportunities").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            opportunities = await client.get_opportunities(candidate_id="abc123")

        assert "contact_id=abc123" in str(route.calls.last.request.url)
        assert len(opportunities) == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_opportunities_with_pagination(self) -> None:
        """Should pass limit and offset parameters."""
        mock_response = {
            "data": [
                {
                    "id": "opp789",
                    "name": "DevOps Engineer",
                },
            ],
            "hasNext": True,
        }

        route = respx.get("https://api.sandbox.lever.co/v1/opportunities").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            opportunities = await client.get_opportunities(limit=10, offset="cursor123")

        url_str = str(route.calls.last.request.url)
        assert "limit=10" in url_str
        assert "offset=cursor123" in url_str
        assert len(opportunities) == 1


class TestLeverClientErrorHandling:
    """Tests for LeverClient error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_unauthorized_error(self) -> None:
        """Should raise LeverAPIError for 401."""
        respx.get("https://api.sandbox.lever.co/v1/candidates").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        async with LeverClient(api_key="bad_key") as client:  # pragma: allowlist secret
            with pytest.raises(LeverAPIError) as exc_info:
                await client.get_applicants()

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @respx.mock
    async def test_forbidden_error(self) -> None:
        """Should raise LeverAPIError for 403."""
        respx.get("https://api.sandbox.lever.co/v1/candidates").mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )

        async with LeverClient(api_key="limited_key") as client:  # pragma: allowlist secret
            with pytest.raises(LeverAPIError) as exc_info:
                await client.get_applicants()

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error_with_retry(self) -> None:
        """Should retry on server errors."""
        route = respx.get("https://api.sandbox.lever.co/v1/candidates")
        route.side_effect = [
            httpx.Response(500, text="Server Error"),
            httpx.Response(200, json={"data": [], "hasNext": False}),
        ]

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicants = await client.get_applicants()

        assert applicants == []
        assert route.call_count == 2


class TestLeverClientDataTransformation:
    """Tests for data transformation from Lever API format."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_extracts_linkedin_url(self) -> None:
        """Should extract LinkedIn URL from links array."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": [
                    "https://github.com/johndoe",
                    "https://linkedin.com/in/johndoe",
                    "https://twitter.com/johndoe",
                ],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        # URL is sanitized to consistent www.linkedin.com format
        assert applicant.linkedin_url == "https://www.linkedin.com/in/johndoe"

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_missing_linkedin(self) -> None:
        """Should handle missing LinkedIn URL."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": ["https://github.com/johndoe"],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.linkedin_url is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_converts_timestamp_to_datetime(self) -> None:
        """Should convert Unix timestamp to datetime."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": [],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,  # 2024-01-01 00:00:00 UTC
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.created_at.year == 2024
        assert applicant.created_at.month == 1
        assert applicant.created_at.day == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_extracts_first_phone(self) -> None:
        """Should extract first phone number from phones array."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [
                    {"value": "+1-555-1234"},
                    {"value": "+1-555-5678"},
                ],
                "links": [],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.phone == "+1-555-1234"

    @pytest.mark.asyncio
    @respx.mock
    async def test_extracts_first_email(self) -> None:
        """Should extract first email from emails array."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["primary@example.com", "secondary@example.com"],
                "phones": [],
                "links": [],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.email == "primary@example.com"


class TestLeverClientLinkedInUrlSanitization:
    """Tests for LinkedIn URL sanitization."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_strips_tracking_parameters_from_linkedin_url(self) -> None:
        """Should strip tracking parameters from LinkedIn URLs."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": ["https://www.linkedin.com/in/johndoe?trk=nav_responsive_tab_profile"],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.linkedin_url == "https://www.linkedin.com/in/johndoe"

    @pytest.mark.asyncio
    @respx.mock
    async def test_keeps_linkedin_job_urls_for_flagging(self) -> None:
        """Should keep LinkedIn job URLs (stripped) for flagging purposes."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": ["https://www.linkedin.com/jobs/view/4358420429/?trackingId=abc123"],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        # Job URLs are kept (stripped) so they can be flagged during validation
        assert applicant.linkedin_url == "https://www.linkedin.com/jobs/view/4358420429"

    @pytest.mark.asyncio
    @respx.mock
    async def test_keeps_linkedin_company_urls_for_flagging(self) -> None:
        """Should keep LinkedIn company URLs for flagging purposes."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": ["https://www.linkedin.com/company/acme-corp"],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        # Company URLs are kept so they can be flagged
        assert applicant.linkedin_url == "https://www.linkedin.com/company/acme-corp"

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_linkedin_pub_urls(self) -> None:
        """Should accept LinkedIn /pub/ profile URLs (older format)."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": ["https://www.linkedin.com/pub/john-doe/12/345/678"],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.linkedin_url == "https://www.linkedin.com/pub/john-doe/12/345/678"

    @pytest.mark.asyncio
    @respx.mock
    async def test_normalizes_linkedin_url_with_trailing_slash(self) -> None:
        """Should normalize LinkedIn URLs with trailing slashes."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": ["https://www.linkedin.com/in/johndoe/"],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        assert applicant.linkedin_url == "https://www.linkedin.com/in/johndoe"

    @pytest.mark.asyncio
    @respx.mock
    async def test_strips_params_from_very_long_linkedin_url(self) -> None:
        """Should strip params from very long LinkedIn URLs to avoid DB overflow."""
        # This is the actual URL pattern that caused the database error
        long_url = (
            "https://www.linkedin.com/jobs/view/4358420429/?trackingId=yHapSTqfQoGHUCezEPnP%2Fg%3D%3D"
            "&refId=UvFhg4TPS6yWXyabrYsCvQ%3D%3D&midToken=AQHJFDwpeMF5lg"
            "&trk=eml-email_job_alert_digest_01-job_position_card-1-cta_url"
            "&trkEmail=eml-email_job_alert_digest_01-job_position_card-1-cta_url"
            "&mcid=6747401789" + "a" * 200  # Add extra characters to make it very long
        )
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": [long_url],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        # URL is kept but stripped of params - well under 500 char limit
        assert applicant.linkedin_url == "https://www.linkedin.com/jobs/view/4358420429"
        assert len(applicant.linkedin_url) < 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_first_linkedin_url_found(self) -> None:
        """When multiple LinkedIn URLs exist, should return the first one found."""
        mock_response = {
            "data": {
                "id": "abc123",
                "name": "John Doe",
                "emails": ["john@example.com"],
                "phones": [],
                "links": [
                    "https://www.linkedin.com/jobs/view/123456",
                    "https://www.linkedin.com/in/johndoe",
                ],
                "location": None,
                "headline": None,
                "sources": [],
                "createdAt": 1704067200000,
                "opportunityIds": ["opp123"],
                "stageChanges": [{"toStageId": "stage1"}],
            }
        }

        respx.get("https://api.sandbox.lever.co/v1/candidates/abc123").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with LeverClient(api_key="test_key") as client:  # pragma: allowlist secret
            applicant = await client.get_applicant("abc123")

        # Returns first LinkedIn URL found (job URL in this case)
        assert applicant.linkedin_url == "https://www.linkedin.com/jobs/view/123456"
