"""Lever ATS API client."""

import base64
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from applicant_validator.clients.base import BaseClient, RetryConfig
from applicant_validator.exceptions import ApplicantNotFoundError, LeverAPIError
from applicant_validator.models import Applicant


class LeverClient(BaseClient):
    """Client for Lever ATS API.

    Lever API documentation: https://hire.lever.co/developer/documentation
    """

    SANDBOX_BASE_URL = "https://api.sandbox.lever.co/v1"
    PRODUCTION_BASE_URL = "https://api.lever.co/v1"

    def __init__(
        self,
        api_key: str,
        environment: str = "sandbox",
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize Lever client.

        Args:
            api_key: Lever API key for authentication.
            environment: Either 'sandbox' or 'production'.
            timeout: Request timeout in seconds.
            retry_config: Configuration for retry behavior.
        """
        self._api_key = api_key
        self._environment = environment

        base_url = self.SANDBOX_BASE_URL if environment == "sandbox" else self.PRODUCTION_BASE_URL

        super().__init__(base_url=base_url, timeout=timeout, retry_config=retry_config)

    @property
    def api_key(self) -> str:
        """Get the API key."""
        return self._api_key

    @property
    def environment(self) -> str:
        """Get the environment (sandbox or production)."""
        return self._environment

    @property
    def service_name(self) -> str:
        """Get the service name for error messages."""
        return "Lever"

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers including Basic Auth."""
        # Lever uses Basic Auth with API key as username and empty password
        credentials = f"{self._api_key}:".encode()
        auth_value = base64.b64encode(credentials).decode()

        return {
            "Authorization": f"Basic {auth_value}",
            "Content-Type": "application/json",
        }

    async def _make_lever_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make request to Lever API with error handling.

        Args:
            method: HTTP method.
            path: API path.
            **kwargs: Additional arguments.

        Returns:
            JSON response.

        Raises:
            LeverAPIError: On API errors.
            ApplicantNotFoundError: When applicant not found (404).
        """
        try:
            return await self._make_request(method, path, **kwargs)
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            if status_code == 404:
                # Extract applicant ID from path if present
                parts = path.split("/")
                applicant_id = parts[-1] if len(parts) > 1 else "unknown"
                raise ApplicantNotFoundError(applicant_id) from e

            raise LeverAPIError(
                message=f"Lever API error: {e.response.text}",
                status_code=status_code,
            ) from e

    def _extract_linkedin_url(self, links: list[str]) -> str | None:
        """Extract LinkedIn URL from list of links.

        Args:
            links: List of URL strings.

        Returns:
            LinkedIn URL if found, None otherwise.
        """
        for link in links:
            if "linkedin.com" in link.lower():
                return link
        return None

    def _parse_candidate(self, data: dict[str, Any]) -> Applicant:
        """Parse Lever candidate data into Applicant model.

        Args:
            data: Raw candidate data from Lever API.

        Returns:
            Applicant model instance.
        """
        # Extract emails (take first)
        emails = data.get("emails", [])
        email = emails[0] if emails else "unknown@example.com"

        # Extract phones (take first value)
        phones = data.get("phones", [])
        phone = phones[0].get("value") if phones else None

        # Extract LinkedIn URL from links
        links = data.get("links", [])
        linkedin_url = self._extract_linkedin_url(links)

        # Convert timestamp (milliseconds to datetime)
        created_at_ms = data.get("createdAt", 0)
        created_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)

        # Get opportunity ID (take first)
        opportunity_ids = data.get("opportunityIds", [])
        opportunity_id = opportunity_ids[0] if opportunity_ids else "unknown"

        # Get stage (from stage changes, take latest)
        stage_changes = data.get("stageChanges", [])
        stage = stage_changes[-1].get("toStageId", "unknown") if stage_changes else "unknown"

        return Applicant(
            id=data["id"],
            name=data.get("name", "Unknown"),
            email=email,
            phone=phone,
            linkedin_url=linkedin_url,
            resume_url=None,  # Would need to fetch separately
            location=data.get("location"),
            company=None,  # Not directly available in candidate endpoint
            headline=data.get("headline"),
            sources=data.get("sources", []),
            created_at=created_at,
            opportunity_id=opportunity_id,
            stage=stage,
        )

    async def get_applicants(
        self,
        limit: int | None = None,
        offset: str | None = None,
    ) -> list[Applicant]:
        """Get list of applicants/candidates from Lever.

        Args:
            limit: Maximum number of candidates to return.
            offset: Pagination cursor for next page.

        Returns:
            List of Applicant models.
        """
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = await self._make_lever_request("GET", "/candidates", params=params)

        candidates = response.get("data", [])
        return [self._parse_candidate(c) for c in candidates]

    async def get_applicant(self, applicant_id: str) -> Applicant:
        """Get single applicant/candidate by ID.

        Args:
            applicant_id: Lever candidate ID.

        Returns:
            Applicant model.

        Raises:
            ApplicantNotFoundError: If applicant not found.
        """
        response = await self._make_lever_request("GET", f"/candidates/{applicant_id}")

        return self._parse_candidate(response.get("data", {}))

    async def get_opportunities(
        self,
        candidate_id: str | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get list of opportunities (job postings).

        Args:
            candidate_id: Filter by candidate ID (contact_id in API).
            limit: Maximum number of opportunities to return.
            offset: Pagination cursor.

        Returns:
            List of opportunity dictionaries.
        """
        params: dict[str, Any] = {}
        if candidate_id is not None:
            params["contact_id"] = candidate_id
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = await self._make_lever_request("GET", "/opportunities", params=params)

        return cast(list[dict[str, Any]], response.get("data", []))
