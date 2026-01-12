"""Tests for sync API routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.sync import (
    ApplicantCountResponse,
    SyncRequest,
    SyncResponse,
    SyncState,
    SyncStatus,
    SyncStatusResponse,
    _sync_state,
    extract_linkedin_url,
    is_linkedin_profile_url,
    router,
    sanitize_linkedin_url,
)


class TestSanitizeLinkedInUrl:
    """Tests for sanitize_linkedin_url helper function."""

    def test_sanitizes_profile_url_with_tracking(self) -> None:
        """Should strip tracking parameters from profile URL."""
        url = "https://www.linkedin.com/in/johndoe?trk=nav_responsive"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_sanitizes_profile_url_with_multiple_params(self) -> None:
        """Should strip all query parameters."""
        url = "https://www.linkedin.com/in/johndoe?param1=a&param2=b&trk=xyz"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_removes_trailing_slash(self) -> None:
        """Should remove trailing slash."""
        url = "https://www.linkedin.com/in/johndoe/"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_handles_pub_profile_url(self) -> None:
        """Should handle older /pub/ profile URLs."""
        url = "https://www.linkedin.com/pub/john-doe/12/345/678"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/pub/john-doe/12/345/678"

    def test_keeps_job_url(self) -> None:
        """Should keep job URLs (for flagging purposes)."""
        url = "https://www.linkedin.com/jobs/view/4358420429?trackingId=abc"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/jobs/view/4358420429"

    def test_keeps_company_url(self) -> None:
        """Should keep company URLs."""
        url = "https://www.linkedin.com/company/acme-corp"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/company/acme-corp"

    def test_returns_none_for_non_linkedin(self) -> None:
        """Should return None for non-LinkedIn URLs."""
        url = "https://github.com/johndoe"
        result = sanitize_linkedin_url(url)
        assert result is None

    def test_returns_none_for_empty_path(self) -> None:
        """Should return None if path is empty."""
        url = "https://www.linkedin.com/"
        result = sanitize_linkedin_url(url)
        assert result is None

    def test_returns_none_for_invalid_url(self) -> None:
        """Should return None for invalid URLs."""
        result = sanitize_linkedin_url("not-a-url")
        assert result is None

    def test_handles_subdomain_variations(self) -> None:
        """Should handle LinkedIn subdomain variations."""
        url = "https://linkedin.com/in/johndoe"
        result = sanitize_linkedin_url(url)
        assert result == "https://www.linkedin.com/in/johndoe"


class TestExtractLinkedInUrl:
    """Tests for extract_linkedin_url helper function."""

    def test_extracts_linkedin_from_list(self) -> None:
        """Should extract LinkedIn URL from list."""
        links = [
            "https://github.com/johndoe",
            "https://www.linkedin.com/in/johndoe",
            "https://twitter.com/johndoe",
        ]
        result = extract_linkedin_url(links)
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_returns_first_linkedin_url(self) -> None:
        """Should return first LinkedIn URL found."""
        links = [
            "https://www.linkedin.com/jobs/view/123",
            "https://www.linkedin.com/in/johndoe",
        ]
        result = extract_linkedin_url(links)
        assert result == "https://www.linkedin.com/jobs/view/123"

    def test_returns_none_if_no_linkedin(self) -> None:
        """Should return None if no LinkedIn URL."""
        links = [
            "https://github.com/johndoe",
            "https://twitter.com/johndoe",
        ]
        result = extract_linkedin_url(links)
        assert result is None

    def test_handles_empty_list(self) -> None:
        """Should handle empty list."""
        result = extract_linkedin_url([])
        assert result is None

    def test_sanitizes_extracted_url(self) -> None:
        """Should sanitize the extracted URL."""
        links = ["https://www.linkedin.com/in/johndoe?trk=tracking"]
        result = extract_linkedin_url(links)
        assert result == "https://www.linkedin.com/in/johndoe"


class TestIsLinkedInProfileUrl:
    """Tests for is_linkedin_profile_url helper function."""

    def test_valid_in_profile(self) -> None:
        """Should return True for /in/ profile URLs."""
        url = "https://www.linkedin.com/in/johndoe"
        assert is_linkedin_profile_url(url) is True

    def test_valid_pub_profile(self) -> None:
        """Should return True for /pub/ profile URLs."""
        url = "https://www.linkedin.com/pub/john-doe/12/345/678"
        assert is_linkedin_profile_url(url) is True

    def test_job_url_not_profile(self) -> None:
        """Should return False for job URLs."""
        url = "https://www.linkedin.com/jobs/view/123456"
        assert is_linkedin_profile_url(url) is False

    def test_company_url_not_profile(self) -> None:
        """Should return False for company URLs."""
        url = "https://www.linkedin.com/company/acme"
        assert is_linkedin_profile_url(url) is False

    def test_returns_false_for_none(self) -> None:
        """Should return False for None."""
        assert is_linkedin_profile_url(None) is False

    def test_returns_false_for_empty_string(self) -> None:
        """Should return False for empty string."""
        assert is_linkedin_profile_url("") is False

    def test_handles_trailing_slash(self) -> None:
        """Should handle trailing slash."""
        url = "https://www.linkedin.com/in/johndoe/"
        assert is_linkedin_profile_url(url) is True


class TestSyncStatusEnum:
    """Tests for SyncStatus enum."""

    def test_sync_status_values(self) -> None:
        """Should have correct status values."""
        assert SyncStatus.IDLE == "idle"
        assert SyncStatus.RUNNING == "running"
        assert SyncStatus.COMPLETED == "completed"
        assert SyncStatus.FAILED == "failed"


class TestSyncStateClass:
    """Tests for SyncState class."""

    def test_initial_state(self) -> None:
        """Should have correct initial values."""
        state = SyncState()
        assert state.status == SyncStatus.IDLE
        assert state.progress == 0
        assert state.total == 0
        assert state.message == ""
        assert state.last_sync_at is None
        assert state.last_sync_count == 0
        assert state.error is None


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_sync_request_default_days(self) -> None:
        """Should default to 7 days."""
        req = SyncRequest()
        assert req.days == 7

    def test_sync_request_custom_days(self) -> None:
        """Should accept custom days value."""
        req = SyncRequest(days=30)
        assert req.days == 30

    def test_sync_request_validation_min(self) -> None:
        """Should reject days < 1."""
        with pytest.raises(ValueError):
            SyncRequest(days=0)

    def test_sync_request_validation_max(self) -> None:
        """Should reject days > 365."""
        with pytest.raises(ValueError):
            SyncRequest(days=400)

    def test_sync_status_response_model(self) -> None:
        """Should create SyncStatusResponse with all fields."""
        resp = SyncStatusResponse(
            status=SyncStatus.COMPLETED,
            progress=100,
            total=100,
            message="Sync complete: 100 applicants",
            last_sync_at=datetime.now(UTC),
            last_sync_count=100,
            error=None,
        )
        assert resp.status == SyncStatus.COMPLETED
        assert resp.progress == 100
        assert resp.total == 100
        assert resp.last_sync_count == 100

    def test_sync_status_response_with_error(self) -> None:
        """Should include error when present."""
        resp = SyncStatusResponse(
            status=SyncStatus.FAILED,
            progress=50,
            total=100,
            message="Sync failed",
            last_sync_at=None,
            last_sync_count=0,
            error="API rate limit exceeded",
        )
        assert resp.status == SyncStatus.FAILED
        assert resp.error == "API rate limit exceeded"

    def test_sync_response_model(self) -> None:
        """Should create SyncResponse with message and status."""
        resp = SyncResponse(
            message="Sync started for last 7 days",
            status=SyncStatus.RUNNING,
        )
        assert "7 days" in resp.message
        assert resp.status == SyncStatus.RUNNING

    def test_applicant_count_response_model(self) -> None:
        """Should create ApplicantCountResponse with count."""
        resp = ApplicantCountResponse(count=1500)
        assert resp.count == 1500


class TestSyncRoutesEndpoints:
    """Tests for sync API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with sync router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_get_sync_status_returns_current_state(self, app: FastAPI) -> None:
        """Should return current sync state."""
        # Reset global state
        _sync_state.status = SyncStatus.IDLE
        _sync_state.progress = 0
        _sync_state.total = 0
        _sync_state.message = ""
        _sync_state.last_sync_at = None
        _sync_state.last_sync_count = 0
        _sync_state.error = None

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["progress"] == 0
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_sync_status_shows_running(self, app: FastAPI) -> None:
        """Should show running status during sync."""
        _sync_state.status = SyncStatus.RUNNING
        _sync_state.progress = 50
        _sync_state.total = 100
        _sync_state.message = "Syncing applicants..."

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["total"] == 100

        # Reset state
        _sync_state.status = SyncStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_sync_when_idle(self, app: FastAPI) -> None:
        """Should start sync and return running status."""
        _sync_state.status = SyncStatus.IDLE

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/sync/start",
                json={"days": 7},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "7 days" in data["message"]

        # Reset state
        _sync_state.status = SyncStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_sync_custom_days(self, app: FastAPI) -> None:
        """Should accept custom days parameter."""
        _sync_state.status = SyncStatus.IDLE

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/sync/start",
                json={"days": 30},
            )

        assert response.status_code == 200
        data = response.json()
        assert "30 days" in data["message"]

        # Reset state
        _sync_state.status = SyncStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_sync_rejects_when_running(self, app: FastAPI) -> None:
        """Should reject sync request when already running."""
        _sync_state.status = SyncStatus.RUNNING

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/sync/start",
                json={"days": 7},
            )

        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"].lower()

        # Reset state
        _sync_state.status = SyncStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_sync_validation_invalid_days(self, app: FastAPI) -> None:
        """Should reject invalid days value."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/sync/start",
                json={"days": 500},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_applicant_count(self, app: FastAPI) -> None:
        """Should return applicant count."""
        with patch("applicant_validator.api.routes.sync.get_session") as mock_session:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 250
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/sync/count")

            assert response.status_code == 200
            data = response.json()
            assert "count" in data
            assert data["count"] == 250

    @pytest.mark.asyncio
    async def test_get_applicant_count_empty_database(self, app: FastAPI) -> None:
        """Should return 0 for empty database."""
        with patch("applicant_validator.api.routes.sync.get_session") as mock_session:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/sync/count")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
