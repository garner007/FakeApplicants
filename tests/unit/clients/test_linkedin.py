"""Tests for LinkedInClient."""

import httpx
import pytest
import respx

from applicant_validator.clients.linkedin import LinkedInClient, LinkedInURLValidator
from applicant_validator.exceptions import LinkedInAPIError


class TestLinkedInURLValidator:
    """Tests for LinkedIn URL validation."""

    def test_valid_standard_url(self) -> None:
        """Should accept standard LinkedIn profile URLs."""
        assert LinkedInURLValidator.is_valid_url("https://linkedin.com/in/johndoe")
        assert LinkedInURLValidator.is_valid_url("https://www.linkedin.com/in/johndoe")
        assert LinkedInURLValidator.is_valid_url("http://linkedin.com/in/johndoe")
        assert LinkedInURLValidator.is_valid_url("http://www.linkedin.com/in/johndoe")

    def test_valid_url_with_dashes(self) -> None:
        """Should accept LinkedIn URLs with dashes in username."""
        assert LinkedInURLValidator.is_valid_url("https://linkedin.com/in/john-doe-123abc")

    def test_valid_url_with_trailing_slash(self) -> None:
        """Should accept URLs with trailing slash."""
        assert LinkedInURLValidator.is_valid_url("https://linkedin.com/in/johndoe/")

    def test_valid_country_specific_url(self) -> None:
        """Should accept country-specific LinkedIn URLs."""
        assert LinkedInURLValidator.is_valid_url("https://uk.linkedin.com/in/johndoe")
        assert LinkedInURLValidator.is_valid_url("https://de.linkedin.com/in/johndoe")

    def test_invalid_url_wrong_domain(self) -> None:
        """Should reject non-LinkedIn URLs."""
        assert not LinkedInURLValidator.is_valid_url("https://example.com/in/johndoe")
        assert not LinkedInURLValidator.is_valid_url("https://fakededin.com/in/user")

    def test_invalid_url_missing_in_path(self) -> None:
        """Should reject LinkedIn URLs without /in/ path."""
        assert not LinkedInURLValidator.is_valid_url("https://linkedin.com/johndoe")
        assert not LinkedInURLValidator.is_valid_url("https://linkedin.com/company/acme")

    def test_invalid_url_empty_username(self) -> None:
        """Should reject URLs without username."""
        assert not LinkedInURLValidator.is_valid_url("https://linkedin.com/in/")
        assert not LinkedInURLValidator.is_valid_url("https://linkedin.com/in")

    def test_invalid_url_format(self) -> None:
        """Should reject malformed URLs."""
        assert not LinkedInURLValidator.is_valid_url("not-a-url")
        assert not LinkedInURLValidator.is_valid_url("")
        assert not LinkedInURLValidator.is_valid_url("linkedin.com/in/user")

    def test_extract_username_standard(self) -> None:
        """Should extract username from standard URL."""
        username = LinkedInURLValidator.extract_username("https://linkedin.com/in/johndoe")
        assert username == "johndoe"

    def test_extract_username_with_trailing_slash(self) -> None:
        """Should extract username from URL with trailing slash."""
        username = LinkedInURLValidator.extract_username("https://linkedin.com/in/johndoe/")
        assert username == "johndoe"

    def test_extract_username_with_query_params(self) -> None:
        """Should extract username ignoring query parameters."""
        username = LinkedInURLValidator.extract_username(
            "https://linkedin.com/in/johndoe?utm_source=share"
        )
        assert username == "johndoe"

    def test_extract_username_invalid_url(self) -> None:
        """Should return None for invalid URLs."""
        assert LinkedInURLValidator.extract_username("not-a-url") is None
        assert LinkedInURLValidator.extract_username("https://example.com") is None


class TestLinkedInClientInit:
    """Tests for LinkedInClient initialization."""

    def test_creation_basic(self) -> None:
        """LinkedInClient should be creatable without OAuth credentials."""
        client = LinkedInClient()
        assert client.service_name == "LinkedIn"

    def test_creation_with_oauth(self) -> None:
        """LinkedInClient should accept OAuth credentials."""
        client = LinkedInClient(
            client_id="my_client_id",
            client_secret="my_secret",
        )
        assert client.client_id == "my_client_id"
        assert client.client_secret == "my_secret"

    def test_has_oauth_credentials(self) -> None:
        """Should check if OAuth credentials are configured."""
        client_no_oauth = LinkedInClient()
        assert not client_no_oauth.has_oauth_credentials

        client_with_oauth = LinkedInClient(client_id="id", client_secret="secret")
        assert client_with_oauth.has_oauth_credentials


class TestLinkedInClientValidateUrl:
    """Tests for LinkedInClient.validate_url()."""

    def test_validate_valid_url(self) -> None:
        """Should return True for valid LinkedIn URLs."""
        client = LinkedInClient()
        assert client.validate_url("https://linkedin.com/in/johndoe") is True

    def test_validate_invalid_url(self) -> None:
        """Should return False for invalid URLs."""
        client = LinkedInClient()
        assert client.validate_url("not-a-url") is False
        assert client.validate_url("https://example.com/user") is False


class TestLinkedInClientCheckProfileExists:
    """Tests for LinkedInClient.check_profile_exists()."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_profile_exists(self) -> None:
        """Should return True for existing profile."""
        respx.head("https://linkedin.com/in/johndoe").mock(return_value=httpx.Response(200))

        async with LinkedInClient() as client:
            exists = await client.check_profile_exists("https://linkedin.com/in/johndoe")

        assert exists is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_profile_not_found(self) -> None:
        """Should return False for 404 response."""
        respx.head("https://linkedin.com/in/nonexistent").mock(return_value=httpx.Response(404))

        async with LinkedInClient() as client:
            exists = await client.check_profile_exists("https://linkedin.com/in/nonexistent")

        assert exists is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_profile_redirect(self) -> None:
        """Should handle redirects (profile exists)."""
        respx.head("https://linkedin.com/in/olduser").mock(
            return_value=httpx.Response(
                301, headers={"Location": "https://linkedin.com/in/newuser"}
            )
        )

        async with LinkedInClient() as client:
            exists = await client.check_profile_exists("https://linkedin.com/in/olduser")

        # Redirects indicate profile exists (moved)
        assert exists is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_profile_rate_limited(self) -> None:
        """Should handle rate limiting."""
        respx.head("https://linkedin.com/in/johndoe").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "60"})
        )

        async with LinkedInClient() as client:
            with pytest.raises(LinkedInAPIError) as exc_info:
                await client.check_profile_exists("https://linkedin.com/in/johndoe")

        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_invalid_url_raises(self) -> None:
        """Should raise error for invalid URL."""
        async with LinkedInClient() as client:
            with pytest.raises(ValueError, match="Invalid LinkedIn URL"):
                await client.check_profile_exists("not-a-valid-url")

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error(self) -> None:
        """Should handle server errors."""
        respx.head("https://linkedin.com/in/johndoe").mock(return_value=httpx.Response(500))

        async with LinkedInClient() as client:
            with pytest.raises(LinkedInAPIError) as exc_info:
                await client.check_profile_exists("https://linkedin.com/in/johndoe")

        assert exc_info.value.status_code == 500


class TestLinkedInClientGetProfilePreview:
    """Tests for LinkedInClient.get_profile_preview()."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_preview_success(self) -> None:
        """Should return basic profile preview data."""
        # Mock the public profile page
        respx.get("https://linkedin.com/in/johndoe").mock(
            return_value=httpx.Response(
                200,
                text="""
                <html>
                <head>
                    <title>John Doe - Software Engineer - Tech Corp | LinkedIn</title>
                    <meta property="og:title" content="John Doe - Software Engineer">
                    <meta property="og:description" content="View John Doe's profile...">
                </head>
                <body></body>
                </html>
                """,
            )
        )

        async with LinkedInClient() as client:
            preview = await client.get_profile_preview("https://linkedin.com/in/johndoe")

        assert preview is not None
        assert "name" in preview
        # The name should be extracted from the title/meta

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_preview_not_found(self) -> None:
        """Should return None for non-existent profile."""
        respx.get("https://linkedin.com/in/nonexistent").mock(return_value=httpx.Response(404))

        async with LinkedInClient() as client:
            preview = await client.get_profile_preview("https://linkedin.com/in/nonexistent")

        assert preview is None

    @pytest.mark.asyncio
    async def test_get_preview_invalid_url(self) -> None:
        """Should raise error for invalid URL."""
        async with LinkedInClient() as client:
            with pytest.raises(ValueError, match="Invalid LinkedIn URL"):
                await client.get_profile_preview("not-a-valid-url")


class TestLinkedInClientFallbackStrategy:
    """Tests for LinkedIn fallback strategy when API unavailable."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_validate_profile_fallback(self) -> None:
        """Should use fallback validation when OAuth unavailable."""
        # Mock HEAD request for existence check
        respx.head("https://linkedin.com/in/johndoe").mock(return_value=httpx.Response(200))

        client = LinkedInClient()  # No OAuth credentials
        async with client:
            result = await client.validate_profile("https://linkedin.com/in/johndoe")

        assert result["exists"] is True
        assert result["validation_method"] == "head_request"

    @pytest.mark.asyncio
    @respx.mock
    async def test_validate_profile_url_format_only(self) -> None:
        """Should validate URL format even if network fails."""
        # Mock network error
        respx.head("https://linkedin.com/in/johndoe").mock(
            side_effect=httpx.ConnectError("Network error")
        )

        client = LinkedInClient()
        async with client:
            result = await client.validate_profile("https://linkedin.com/in/johndoe")

        assert result["url_valid"] is True
        assert result["exists"] is None  # Unknown due to network error
        assert "error" in result

    @pytest.mark.asyncio
    async def test_validate_profile_invalid_url(self) -> None:
        """Should fail validation for invalid URL format."""
        client = LinkedInClient()
        async with client:
            result = await client.validate_profile("not-a-linkedin-url")

        assert result["url_valid"] is False
        assert result["exists"] is False


class TestLinkedInClientAdditionalCoverage:
    """Additional tests for edge cases and coverage."""

    def test_access_token_in_headers(self) -> None:
        """Should include access token in headers when provided."""
        client = LinkedInClient(access_token="test_token_123")
        headers = client._get_default_headers()
        assert headers["Authorization"] == "Bearer test_token_123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_preview_non_200_response(self) -> None:
        """Should return None for non-200, non-404 responses."""
        respx.get("https://linkedin.com/in/johndoe").mock(return_value=httpx.Response(500))

        async with LinkedInClient() as client:
            preview = await client.get_profile_preview("https://linkedin.com/in/johndoe")

        assert preview is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_preview_title_fallback(self) -> None:
        """Should extract name from title tag when og:title missing."""
        respx.get("https://linkedin.com/in/johndoe").mock(
            return_value=httpx.Response(
                200,
                text="""
                <html>
                <head>
                    <title>Jane Smith - Data Scientist | LinkedIn</title>
                </head>
                <body></body>
                </html>
                """,
            )
        )

        async with LinkedInClient() as client:
            preview = await client.get_profile_preview("https://linkedin.com/in/johndoe")

        assert preview is not None
        assert preview["name"] == "Jane Smith"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_preview_no_name_found(self) -> None:
        """Should return None when no name can be extracted."""
        respx.get("https://linkedin.com/in/johndoe").mock(
            return_value=httpx.Response(
                200,
                text="""
                <html>
                <head>
                    <title></title>
                </head>
                <body></body>
                </html>
                """,
            )
        )

        async with LinkedInClient() as client:
            preview = await client.get_profile_preview("https://linkedin.com/in/johndoe")

        assert preview is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_preview_network_error(self) -> None:
        """Should return None on network errors."""
        respx.get("https://linkedin.com/in/johndoe").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        async with LinkedInClient() as client:
            preview = await client.get_profile_preview("https://linkedin.com/in/johndoe")

        assert preview is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_check_profile_http_status_error(self) -> None:
        """Should handle HTTPStatusError in check_profile_exists."""
        # Mock raises HTTPStatusError
        respx.head("https://linkedin.com/in/johndoe").mock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("HEAD", "https://linkedin.com/in/johndoe"),
                response=httpx.Response(503),
            )
        )

        async with LinkedInClient() as client:
            with pytest.raises(LinkedInAPIError) as exc_info:
                await client.check_profile_exists("https://linkedin.com/in/johndoe")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @respx.mock
    async def test_check_profile_generic_http_error(self) -> None:
        """Should handle generic HTTPError in check_profile_exists."""
        respx.head("https://linkedin.com/in/johndoe").mock(side_effect=httpx.ReadTimeout("Timeout"))

        async with LinkedInClient() as client:
            with pytest.raises(LinkedInAPIError) as exc_info:
                await client.check_profile_exists("https://linkedin.com/in/johndoe")

        assert "Timeout" in str(exc_info.value)
