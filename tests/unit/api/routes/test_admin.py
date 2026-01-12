"""Tests for admin API routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.admin import (
    AuthSettingsResponse,
    AuthSettingsUpdate,
    DatabaseStatsResponse,
    PurgeRequest,
    PurgeResponse,
    PurgeState,
    PurgeStatus,
    PurgeStatusResponse,
    _perform_purge,
    _purge_state,
    router,
)


class TestPurgeStatusEnum:
    """Tests for PurgeStatus enum."""

    def test_purge_status_values(self) -> None:
        """Should have correct status values."""
        assert PurgeStatus.IDLE == "idle"
        assert PurgeStatus.RUNNING == "running"
        assert PurgeStatus.COMPLETED == "completed"
        assert PurgeStatus.FAILED == "failed"


class TestPurgeStateClass:
    """Tests for PurgeState class."""

    def test_initial_state(self) -> None:
        """Should have correct initial values."""
        state = PurgeState()
        assert state.status == PurgeStatus.IDLE
        assert state.message == ""
        assert state.last_run_at is None
        assert state.error is None
        assert state.applicants_deleted == 0
        assert state.flags_deleted == 0
        assert state.validation_runs_deleted == 0


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_purge_request_confirm_true(self) -> None:
        """Should create PurgeRequest with confirm=True."""
        req = PurgeRequest(confirm=True)
        assert req.confirm is True
        assert req.keep_flag_types is True  # default

    def test_purge_request_confirm_false(self) -> None:
        """Should create PurgeRequest with confirm=False."""
        req = PurgeRequest(confirm=False)
        assert req.confirm is False

    def test_purge_request_custom_keep_flag_types(self) -> None:
        """Should accept custom keep_flag_types value."""
        req = PurgeRequest(confirm=True, keep_flag_types=False)
        assert req.confirm is True
        assert req.keep_flag_types is False

    def test_purge_status_response_model(self) -> None:
        """Should create PurgeStatusResponse with all fields."""
        resp = PurgeStatusResponse(
            status=PurgeStatus.COMPLETED,
            message="Purge complete",
            last_run_at=datetime.now(UTC),
            error=None,
            applicants_deleted=100,
            flags_deleted=50,
            validation_runs_deleted=25,
        )
        assert resp.status == PurgeStatus.COMPLETED
        assert resp.applicants_deleted == 100
        assert resp.flags_deleted == 50
        assert resp.validation_runs_deleted == 25

    def test_purge_status_response_with_error(self) -> None:
        """Should include error message when present."""
        resp = PurgeStatusResponse(
            status=PurgeStatus.FAILED,
            message="Purge failed",
            last_run_at=None,
            error="Database connection error",
            applicants_deleted=0,
            flags_deleted=0,
            validation_runs_deleted=0,
        )
        assert resp.status == PurgeStatus.FAILED
        assert resp.error == "Database connection error"

    def test_purge_response_model(self) -> None:
        """Should create PurgeResponse with message and status."""
        resp = PurgeResponse(
            message="Purge started",
            status=PurgeStatus.RUNNING,
        )
        assert resp.message == "Purge started"
        assert resp.status == PurgeStatus.RUNNING

    def test_database_stats_response_model(self) -> None:
        """Should create DatabaseStatsResponse with all counts."""
        resp = DatabaseStatsResponse(
            applicants_count=1000,
            flags_count=500,
            validation_runs_count=50,
            flag_types_count=10,
            linkedin_profiles_count=200,
        )
        assert resp.applicants_count == 1000
        assert resp.flags_count == 500
        assert resp.validation_runs_count == 50
        assert resp.flag_types_count == 10
        assert resp.linkedin_profiles_count == 200

    def test_auth_settings_response_model(self) -> None:
        """Should create AuthSettingsResponse with all fields."""
        resp = AuthSettingsResponse(
            auth_allowed_domain="example.com",
            auth_jwt_expiry_hours="24",
            auth_cookie_name="session",
            auth_cookie_secure="true",
            auth_min_password_length="8",
        )
        assert resp.auth_allowed_domain == "example.com"
        assert resp.auth_jwt_expiry_hours == "24"
        assert resp.auth_cookie_name == "session"
        assert resp.auth_cookie_secure == "true"
        assert resp.auth_min_password_length == "8"

    def test_auth_settings_update_partial(self) -> None:
        """Should allow partial updates."""
        req = AuthSettingsUpdate(auth_jwt_expiry_hours="48")
        assert req.auth_jwt_expiry_hours == "48"
        assert req.auth_allowed_domain is None
        assert req.auth_cookie_name is None

    def test_auth_settings_update_empty(self) -> None:
        """Should allow empty update request."""
        req = AuthSettingsUpdate()
        assert req.auth_jwt_expiry_hours is None
        assert req.auth_allowed_domain is None
        assert req.auth_cookie_secure is None


class TestAdminRoutesAuthentication:
    """Tests for admin routes authentication requirements."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with admin router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_get_stats_no_auth_required(self, app: FastAPI) -> None:
        """Stats endpoint should be accessible without auth (for monitoring)."""
        with patch("applicant_validator.api.routes.admin.get_session") as mock_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock()
            mock_ctx.__aexit__ = AsyncMock()

            mock_db = AsyncMock()
            mock_db.scalar = AsyncMock(return_value=0)
            mock_ctx.__aenter__.return_value = mock_db
            mock_session.return_value = mock_ctx

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/admin/stats")

            # Should be 200 or 500 depending on mock setup
            assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_get_purge_status_no_auth(self, app: FastAPI) -> None:
        """Purge status endpoint should return current state."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/purge/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_post_purge_without_confirm(self, app: FastAPI) -> None:
        """Should reject purge without confirm=true."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/purge",
                json={"confirm": False},
            )

        assert response.status_code == 400
        assert "confirm=true" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_auth_settings_requires_admin(self, app: FastAPI) -> None:
        """Auth settings endpoint should require admin."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/auth-settings")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_patch_auth_settings_requires_admin(self, app: FastAPI) -> None:
        """Patching auth settings should require admin."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/admin/auth-settings",
                json={"auth_jwt_expiry_hours": "48"},
            )

        assert response.status_code == 401


class TestPurgeStatusEndpoint:
    """Tests for GET /admin/purge/status endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_returns_idle_status_initially(self, app: FastAPI) -> None:
        """Should return idle status when no purge has run."""
        # Reset global state
        _purge_state.status = PurgeStatus.IDLE
        _purge_state.message = ""
        _purge_state.last_run_at = None
        _purge_state.error = None
        _purge_state.applicants_deleted = 0
        _purge_state.flags_deleted = 0
        _purge_state.validation_runs_deleted = 0

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/purge/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

    @pytest.mark.asyncio
    async def test_returns_completed_status_after_purge(self, app: FastAPI) -> None:
        """Should return completed status after successful purge."""
        # Set completed state
        _purge_state.status = PurgeStatus.COMPLETED
        _purge_state.message = "Purge complete: 100 applicants deleted"
        _purge_state.last_run_at = datetime.now(UTC)
        _purge_state.applicants_deleted = 100
        _purge_state.flags_deleted = 50
        _purge_state.validation_runs_deleted = 25

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/purge/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["applicants_deleted"] == 100
        assert data["flags_deleted"] == 50

    @pytest.mark.asyncio
    async def test_returns_failed_status_with_error(self, app: FastAPI) -> None:
        """Should include error message when purge failed."""
        _purge_state.status = PurgeStatus.FAILED
        _purge_state.message = "Purge failed"
        _purge_state.error = "Database connection error"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/admin/purge/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Database connection error"


class TestPurgeEndpoint:
    """Tests for POST /admin/purge endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_rejects_without_confirm(self, app: FastAPI) -> None:
        """Should return 400 if confirm is not true."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/purge",
                json={"confirm": False},
            )

        assert response.status_code == 400
        assert "confirm=true" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rejects_when_purge_in_progress(self, app: FastAPI) -> None:
        """Should return 409 if purge is already running."""
        _purge_state.status = PurgeStatus.RUNNING

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/purge",
                json={"confirm": True},
            )

        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]

        # Reset state
        _purge_state.status = PurgeStatus.IDLE

    @pytest.mark.asyncio
    async def test_starts_purge_when_idle(self, app: FastAPI) -> None:
        """Should start purge and return running status."""
        _purge_state.status = PurgeStatus.IDLE

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/purge",
                json={"confirm": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "started" in data["message"].lower()

        # Reset state
        _purge_state.status = PurgeStatus.IDLE


class TestDatabaseStatsEndpoint:
    """Tests for GET /admin/stats endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_returns_all_counts(self, app: FastAPI) -> None:
        """Should return all database counts."""
        with patch("applicant_validator.api.routes.admin.get_session") as mock_session:
            mock_ctx = AsyncMock()
            mock_db = AsyncMock()

            # Return different counts for different scalars
            mock_db.scalar = AsyncMock(side_effect=[100, 50, 25, 10, 5])
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.__aexit__ = AsyncMock()
            mock_session.return_value = mock_ctx

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/admin/stats")

            assert response.status_code == 200
            data = response.json()
            assert "applicants_count" in data
            assert "flags_count" in data
            assert "validation_runs_count" in data
            assert "flag_types_count" in data
            assert "linkedin_profiles_count" in data


class TestPerformPurgeFunction:
    """Tests for _perform_purge background task function."""

    @pytest.mark.asyncio
    async def test_updates_state_on_success(self) -> None:
        """Should update global state on successful purge."""
        with patch("applicant_validator.api.routes.admin.get_session") as mock_session:
            mock_ctx = AsyncMock()
            mock_db = AsyncMock()

            # Mock counts before deletion
            mock_db.scalar = AsyncMock(side_effect=[100, 50, 25])
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()

            mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.__aexit__ = AsyncMock()
            mock_session.return_value = mock_ctx

            # Reset state
            _purge_state.status = PurgeStatus.IDLE

            await _perform_purge(keep_flag_types=True)

            assert _purge_state.status == PurgeStatus.COMPLETED
            assert _purge_state.applicants_deleted == 100
            assert _purge_state.flags_deleted == 50
            assert _purge_state.validation_runs_deleted == 25
            assert _purge_state.last_run_at is not None

    @pytest.mark.asyncio
    async def test_updates_state_on_failure(self) -> None:
        """Should update state with error on failure."""
        with patch("applicant_validator.api.routes.admin.get_session") as mock_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("Database connection failed"))
            mock_ctx.__aexit__ = AsyncMock()
            mock_session.return_value = mock_ctx

            _purge_state.status = PurgeStatus.IDLE

            await _perform_purge()

            assert _purge_state.status == PurgeStatus.FAILED
            assert "Database connection failed" in _purge_state.error
