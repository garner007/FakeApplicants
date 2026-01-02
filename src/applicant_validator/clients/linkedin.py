"""LinkedIn API client with fallback strategies."""

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from applicant_validator.clients.base import BaseClient, RetryConfig
from applicant_validator.exceptions import LinkedInAPIError


class LinkedInURLValidator:
    """Utility class for validating LinkedIn URLs."""

    # Pattern for LinkedIn profile URLs
    PROFILE_URL_PATTERN = re.compile(
        r"^https?://(?:[\w-]+\.)?linkedin\.com/in/[\w-]+/?(?:\?.*)?$",
        re.IGNORECASE,
    )

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """Check if URL is a valid LinkedIn profile URL.

        Args:
            url: URL string to validate.

        Returns:
            True if valid LinkedIn profile URL, False otherwise.
        """
        if not url:
            return False

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False

        return bool(cls.PROFILE_URL_PATTERN.match(url))

    @classmethod
    def extract_username(cls, url: str) -> str | None:
        """Extract LinkedIn username from profile URL.

        Args:
            url: LinkedIn profile URL.

        Returns:
            Username string or None if extraction fails.
        """
        if not cls.is_valid_url(url):
            return None

        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            parts = path.split("/")
            # Path should be /in/username
            if len(parts) >= 3 and parts[1] == "in":
                return parts[2]
        except Exception:
            pass

        return None


class LinkedInClient(BaseClient):
    """Client for LinkedIn API with fallback strategies.

    Since LinkedIn API access is restricted, this client provides:
    1. URL format validation
    2. Profile existence checking via HEAD requests
    3. Basic profile preview from public pages
    4. Full API access when OAuth credentials are provided
    """

    BASE_URL = "https://api.linkedin.com/v2"
    PUBLIC_PROFILE_URL = "https://linkedin.com"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize LinkedIn client.

        Args:
            client_id: OAuth client ID (optional).
            client_secret: OAuth client secret (optional).
            access_token: OAuth access token (optional).
            timeout: Request timeout in seconds.
            retry_config: Configuration for retry behavior.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token

        super().__init__(
            base_url=self.BASE_URL,
            timeout=timeout,
            retry_config=retry_config or RetryConfig(max_retries=2, base_delay=0.5),
        )

    @property
    def client_id(self) -> str | None:
        """Get OAuth client ID."""
        return self._client_id

    @property
    def client_secret(self) -> str | None:
        """Get OAuth client secret."""
        return self._client_secret

    @property
    def has_oauth_credentials(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self._client_id and self._client_secret)

    @property
    def service_name(self) -> str:
        """Get service name for error messages."""
        return "LinkedIn"

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests."""
        headers: dict[str, str] = {
            "User-Agent": "ApplicantValidator/1.0",
        }

        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    def validate_url(self, url: str) -> bool:
        """Validate LinkedIn profile URL format.

        Args:
            url: URL to validate.

        Returns:
            True if valid LinkedIn profile URL.
        """
        return LinkedInURLValidator.is_valid_url(url)

    async def check_profile_exists(self, url: str) -> bool:
        """Check if a LinkedIn profile exists by making HEAD request.

        Args:
            url: LinkedIn profile URL.

        Returns:
            True if profile exists, False otherwise.

        Raises:
            ValueError: If URL is not a valid LinkedIn URL.
            LinkedInAPIError: On API errors (rate limiting, server errors).
        """
        if not self.validate_url(url):
            msg = f"Invalid LinkedIn URL: {url}"
            raise ValueError(msg)

        try:
            response = await self._client.head(url, follow_redirects=False)

            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            elif response.status_code in (301, 302, 303, 307, 308):
                # Redirects indicate profile exists (possibly moved)
                return True
            elif response.status_code == 429:
                raise LinkedInAPIError(
                    message="Rate limited by LinkedIn",
                    status_code=429,
                )
            else:
                raise LinkedInAPIError(
                    message=f"LinkedIn returned status {response.status_code}",
                    status_code=response.status_code,
                )

        except httpx.HTTPError as e:
            if isinstance(e, httpx.HTTPStatusError):
                raise LinkedInAPIError(
                    message=str(e),
                    status_code=e.response.status_code,
                ) from e
            raise LinkedInAPIError(message=str(e)) from e

    async def get_profile_preview(self, url: str) -> dict[str, Any] | None:
        """Get basic profile preview from public page.

        This is a fallback when full API access is unavailable.
        Extracts name and headline from public profile page metadata.

        Args:
            url: LinkedIn profile URL.

        Returns:
            Dict with profile preview data, or None if unavailable.

        Raises:
            ValueError: If URL is not valid.
        """
        if not self.validate_url(url):
            msg = f"Invalid LinkedIn URL: {url}"
            raise ValueError(msg)

        try:
            response = await self._client.get(url, follow_redirects=True)

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                return None

            # Parse basic info from HTML
            content = response.text
            preview: dict[str, Any] = {}

            # Extract from og:title meta tag
            og_title_match = re.search(
                r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
                content,
                re.IGNORECASE,
            )
            if og_title_match:
                title = og_title_match.group(1)
                # Title format: "Name - Headline | LinkedIn"
                parts = title.split(" - ", 1)
                if parts:
                    preview["name"] = parts[0].strip()
                    if len(parts) > 1:
                        headline = parts[1].split(" | ")[0].strip()
                        preview["headline"] = headline

            # Try title tag as fallback
            if "name" not in preview:
                title_match = re.search(
                    r"<title>([^<]+)</title>",
                    content,
                    re.IGNORECASE,
                )
                if title_match:
                    title = title_match.group(1)
                    parts = title.split(" - ", 1)
                    if parts:
                        preview["name"] = parts[0].strip()

            preview["url"] = url
            preview["username"] = LinkedInURLValidator.extract_username(url)

            return preview if preview.get("name") else None

        except httpx.HTTPError:
            return None

    async def validate_profile(self, url: str) -> dict[str, Any]:
        """Validate a LinkedIn profile with available methods.

        Uses fallback strategy when full API is unavailable.

        Args:
            url: LinkedIn profile URL.

        Returns:
            Dict with validation results including:
            - url_valid: Whether URL format is valid
            - exists: Whether profile exists (True/False/None if unknown)
            - validation_method: Method used for validation
            - error: Error message if any
        """
        result: dict[str, Any] = {
            "url": url,
            "url_valid": self.validate_url(url),
            "exists": False,
            "validation_method": "none",
        }

        if not result["url_valid"]:
            return result

        # Try HEAD request to check existence
        try:
            exists = await self.check_profile_exists(url)
            result["exists"] = exists
            result["validation_method"] = "head_request"
        except LinkedInAPIError as e:
            result["exists"] = None
            result["error"] = str(e)
            result["validation_method"] = "head_request_failed"
        except httpx.ConnectError as e:
            result["exists"] = None
            result["error"] = f"Network error: {e}"
            result["validation_method"] = "head_request_failed"

        return result
