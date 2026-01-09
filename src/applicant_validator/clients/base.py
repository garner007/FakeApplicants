"""Base HTTP client with retry logic and common functionality."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, cast

import httpx

from applicant_validator.exceptions import RateLimitExceededError


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


class BaseClient(ABC):
    """Abstract base class for API clients with retry logic."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize the base client.

        Args:
            base_url: Base URL for the API.
            timeout: Request timeout in seconds.
            retry_config: Configuration for retry behavior.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry_config = retry_config or RetryConfig()
        self.__client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url

    @property
    def timeout(self) -> float:
        """Get the timeout setting."""
        return self._timeout

    @property
    def retry_config(self) -> RetryConfig:
        """Get the retry configuration."""
        return self._retry_config

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Get the service name for error messages."""
        pass

    @property
    def _client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self.__client is None:
            self.__client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._get_default_headers(),
            )
        return self.__client

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests. Override in subclasses."""
        return {}

    def _build_url(self, path: str) -> str:
        """Build full URL from path.

        Args:
            path: API path (with or without leading slash).

        Returns:
            Full URL.
        """
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self._base_url}{path}"

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay for retry attempt.

        Args:
            attempt: Zero-based attempt number.

        Returns:
            Delay in seconds.
        """
        delay = self._retry_config.base_delay * (self._retry_config.exponential_base**attempt)
        return min(delay, self._retry_config.max_delay)

    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code.

        Args:
            status_code: HTTP status code.

        Returns:
            True if should retry, False otherwise.
        """
        # Retry on server errors (5xx) but not client errors (4xx)
        # Exception: 429 is handled separately
        return status_code >= 500

    async def _handle_rate_limit(self, response: httpx.Response) -> None:
        """Handle 429 rate limit response.

        Args:
            response: The HTTP response.

        Raises:
            RateLimitExceededError: Always raised with retry info.
        """
        retry_after = response.headers.get("Retry-After")
        retry_seconds = int(retry_after) if retry_after else None

        raise RateLimitExceededError(
            service=self.service_name,
            retry_after=retry_seconds,
        )

    async def _make_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path.
            **kwargs: Additional arguments passed to httpx.

        Returns:
            JSON response as dict.

        Raises:
            httpx.HTTPStatusError: If request fails after retries.
            RateLimitExceededError: If rate limited.
        """
        url = self._build_url(path)
        last_exception: Exception | None = None

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                request_method = getattr(self._client, method.lower())
                response: httpx.Response = await request_method(url, **kwargs)

                # Check for rate limiting
                if response.status_code == 429:
                    await self._handle_rate_limit(response)

                # Raise for other error statuses
                response.raise_for_status()

                return cast("dict[str, Any]", response.json())

            except httpx.HTTPStatusError as e:
                last_exception = e

                # Don't retry on client errors (4xx) except 429 which is handled above
                if not self._should_retry(e.response.status_code):
                    raise

                # Retry on server errors
                if attempt < self._retry_config.max_retries:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        # This should not be reached, but satisfy type checker
        if last_exception:
            raise last_exception
        msg = "Request failed with no exception"
        raise RuntimeError(msg)

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make GET request.

        Args:
            path: API path.
            params: Query parameters.
            headers: Additional headers.
            **kwargs: Additional arguments.

        Returns:
            JSON response.
        """
        return await self._make_request(
            "GET",
            path,
            params=params,
            headers=headers,
            **kwargs,
        )

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make POST request.

        Args:
            path: API path.
            json: JSON body.
            headers: Additional headers.
            **kwargs: Additional arguments.

        Returns:
            JSON response.
        """
        return await self._make_request(
            "POST",
            path,
            json=json,
            headers=headers,
            **kwargs,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self.__client is not None:
            await self.__client.aclose()
            self.__client = None

    async def __aenter__(self) -> "BaseClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
