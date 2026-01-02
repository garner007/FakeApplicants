"""Tests for BaseClient abstract class."""

import json

import httpx
import pytest
import respx

from applicant_validator.clients.base import BaseClient, RetryConfig
from applicant_validator.exceptions import RateLimitExceededError


class ConcreteClient(BaseClient):
    """Concrete implementation for testing abstract BaseClient."""

    def __init__(
        self,
        base_url: str = "https://api.example.com",
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        super().__init__(base_url=base_url, timeout=timeout, retry_config=retry_config)

    @property
    def service_name(self) -> str:
        return "TestService"


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self) -> None:
        """RetryConfig should have sensible defaults."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0

    def test_custom_values(self) -> None:
        """RetryConfig should accept custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0


class TestBaseClient:
    """Tests for BaseClient abstract class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """BaseClient should not be directly instantiable."""
        with pytest.raises(TypeError):
            BaseClient(base_url="https://api.example.com")  # type: ignore[abstract]

    def test_concrete_client_creation(self) -> None:
        """Concrete implementation should be instantiable."""
        client = ConcreteClient()
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30.0
        assert client.service_name == "TestService"

    def test_custom_timeout(self) -> None:
        """Client should accept custom timeout."""
        client = ConcreteClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_custom_retry_config(self) -> None:
        """Client should accept custom retry config."""
        config = RetryConfig(max_retries=5)
        client = ConcreteClient(retry_config=config)
        assert client.retry_config.max_retries == 5

    def test_default_retry_config(self) -> None:
        """Client should have default retry config if not provided."""
        client = ConcreteClient()
        assert client.retry_config is not None
        assert client.retry_config.max_retries == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request_success(self) -> None:
        """Client should successfully make GET requests."""
        respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(200, json={"data": "test"})
        )

        async with ConcreteClient() as client:
            response = await client.get("/test")

        assert response == {"data": "test"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_request_success(self) -> None:
        """Client should successfully make POST requests."""
        respx.post("https://api.example.com/test").mock(
            return_value=httpx.Response(200, json={"created": True})
        )

        async with ConcreteClient() as client:
            response = await client.post("/test", json={"name": "test"})

        assert response == {"created": True}

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_server_error(self) -> None:
        """Client should retry on 5xx server errors."""
        route = respx.get("https://api.example.com/test")
        route.side_effect = [
            httpx.Response(500, text="Server Error"),
            httpx.Response(200, json={"data": "success"}),
        ]

        async with ConcreteClient(
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        ) as client:
            response = await client.get("/test")

        assert response == {"data": "success"}
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_exhausted(self) -> None:
        """Client should raise after max retries exhausted."""
        respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(500, text="Server Error")
        )

        async with ConcreteClient(
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        ) as client:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await client.get("/test")

        assert exc_info.value.response.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_retry_on_client_error(self) -> None:
        """Client should not retry on 4xx client errors (except 429)."""
        route = respx.get("https://api.example.com/test")
        route.mock(return_value=httpx.Response(400, text="Bad Request"))

        async with ConcreteClient(
            retry_config=RetryConfig(max_retries=3, base_delay=0.01)
        ) as client:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await client.get("/test")

        # Should only try once (no retries for 4xx)
        assert route.call_count == 1
        assert exc_info.value.response.status_code == 400

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_handling(self) -> None:
        """Client should handle 429 rate limit responses."""
        respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(
                429,
                text="Too Many Requests",
                headers={"Retry-After": "30"},
            )
        )

        async with ConcreteClient(
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        ) as client:
            with pytest.raises(RateLimitExceededError) as exc_info:
                await client.get("/test")

        assert exc_info.value.service == "TestService"
        assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_without_retry_after(self) -> None:
        """Client should handle 429 without Retry-After header."""
        respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        async with ConcreteClient(
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        ) as client:
            with pytest.raises(RateLimitExceededError) as exc_info:
                await client.get("/test")

        assert exc_info.value.retry_after is None

    def test_exponential_backoff_calculation(self) -> None:
        """Client should calculate exponential backoff correctly."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=60.0)
        client = ConcreteClient(retry_config=config)

        # Test backoff calculation
        assert client._calculate_backoff(0) == 1.0  # 1 * 2^0 = 1
        assert client._calculate_backoff(1) == 2.0  # 1 * 2^1 = 2
        assert client._calculate_backoff(2) == 4.0  # 1 * 2^2 = 4
        assert client._calculate_backoff(3) == 8.0  # 1 * 2^3 = 8

    def test_backoff_respects_max_delay(self) -> None:
        """Backoff should not exceed max_delay."""
        config = RetryConfig(base_delay=10.0, exponential_base=2.0, max_delay=30.0)
        client = ConcreteClient(retry_config=config)

        # 10 * 2^3 = 80, but should be capped at 30
        assert client._calculate_backoff(3) == 30.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_context_manager(self) -> None:
        """Client should work as async context manager."""
        respx.get("https://api.example.com/test").mock(return_value=httpx.Response(200, json={}))

        async with ConcreteClient() as client:
            assert client is not None
            assert client.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Client should close underlying httpx client."""
        client = ConcreteClient()
        # Access _client to initialize it
        _ = client._client

        # Should not raise
        await client.close()

        # Should be able to close again without error
        await client.close()

    def test_build_url(self) -> None:
        """Client should build full URLs correctly."""
        client = ConcreteClient(base_url="https://api.example.com/v1")

        assert client._build_url("/users") == "https://api.example.com/v1/users"
        assert client._build_url("users") == "https://api.example.com/v1/users"

    def test_build_url_strips_trailing_slash(self) -> None:
        """Client should handle trailing slashes in base URL."""
        client = ConcreteClient(base_url="https://api.example.com/v1/")

        assert client._build_url("/users") == "https://api.example.com/v1/users"

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_headers(self) -> None:
        """Client should allow custom headers per request."""
        route = respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(200, json={})
        )

        async with ConcreteClient() as client:
            await client.get("/test", headers={"X-Custom": "value"})

        # Check that headers were passed
        assert route.calls.last.request.headers["X-Custom"] == "value"

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_params(self) -> None:
        """Client should pass query parameters correctly."""
        route = respx.get("https://api.example.com/test").mock(
            return_value=httpx.Response(200, json={})
        )

        async with ConcreteClient() as client:
            await client.get("/test", params={"limit": 10, "offset": 0})

        # Check that params were passed
        assert "limit=10" in str(route.calls.last.request.url)
        assert "offset=0" in str(route.calls.last.request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_with_json_body(self) -> None:
        """Client should send JSON body in POST requests."""
        route = respx.post("https://api.example.com/test").mock(
            return_value=httpx.Response(201, json={"id": "123"})
        )

        async with ConcreteClient() as client:
            response = await client.post("/test", json={"name": "test"})

        assert response == {"id": "123"}
        request_body = json.loads(route.calls.last.request.content)
        assert request_body == {"name": "test"}
