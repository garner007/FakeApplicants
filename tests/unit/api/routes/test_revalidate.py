"""Tests for revalidate API routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.revalidate import (
    RevalidateRequest,
    RevalidateResponse,
    RevalidateState,
    RevalidateStatus,
    RevalidateStatusResponse,
    _perform_revalidation,
    _revalidate_state,
    router,
)


class TestRevalidateStatusEnum:
    """Tests for RevalidateStatus enum."""

    def test_revalidate_status_values(self) -> None:
        """Should have correct status values."""
        assert RevalidateStatus.IDLE == "idle"
        assert RevalidateStatus.RUNNING == "running"
        assert RevalidateStatus.COMPLETED == "completed"
        assert RevalidateStatus.FAILED == "failed"


class TestRevalidateStateClass:
    """Tests for RevalidateState class."""

    def test_initial_state(self) -> None:
        """Should have correct initial values."""
        state = RevalidateState()
        assert state.status == RevalidateStatus.IDLE
        assert state.progress == 0
        assert state.total == 0
        assert state.message == ""
        assert state.last_run_at is None
        assert state.error is None
        assert state.applicants_processed == 0
        assert state.flags_raised == 0
        assert state.flags_cleared == 0
        assert state.risk_level_changes == 0
        assert state.current_applicant_name is None


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_revalidate_request_defaults(self) -> None:
        """Should have correct default values."""
        req = RevalidateRequest()
        assert req.days is None
        assert req.clear_existing_flags is True

    def test_revalidate_request_custom_days(self) -> None:
        """Should accept custom days value."""
        req = RevalidateRequest(days=30)
        assert req.days == 30

    def test_revalidate_request_validation_min(self) -> None:
        """Should reject days < 1."""
        with pytest.raises(ValueError):
            RevalidateRequest(days=0)

    def test_revalidate_request_validation_max(self) -> None:
        """Should reject days > 365."""
        with pytest.raises(ValueError):
            RevalidateRequest(days=400)

    def test_revalidate_request_clear_flags_false(self) -> None:
        """Should accept clear_existing_flags=False."""
        req = RevalidateRequest(clear_existing_flags=False)
        assert req.clear_existing_flags is False

    def test_revalidate_status_response_model(self) -> None:
        """Should create RevalidateStatusResponse with all fields."""
        resp = RevalidateStatusResponse(
            status=RevalidateStatus.COMPLETED,
            progress=100,
            total=100,
            message="Re-validation complete",
            last_run_at=datetime.now(UTC),
            error=None,
            applicants_processed=100,
            flags_raised=50,
            flags_cleared=75,
            risk_level_changes=25,
            current_applicant_name=None,
        )
        assert resp.status == RevalidateStatus.COMPLETED
        assert resp.applicants_processed == 100
        assert resp.flags_raised == 50
        assert resp.flags_cleared == 75
        assert resp.risk_level_changes == 25

    def test_revalidate_status_response_with_error(self) -> None:
        """Should include error when present."""
        resp = RevalidateStatusResponse(
            status=RevalidateStatus.FAILED,
            progress=50,
            total=100,
            message="Re-validation failed",
            last_run_at=None,
            error="Database error",
            applicants_processed=50,
            flags_raised=20,
            flags_cleared=30,
            risk_level_changes=10,
            current_applicant_name="John Doe",
        )
        assert resp.status == RevalidateStatus.FAILED
        assert resp.error == "Database error"
        assert resp.current_applicant_name == "John Doe"

    def test_revalidate_response_model(self) -> None:
        """Should create RevalidateResponse with message and status."""
        resp = RevalidateResponse(
            message="Re-validation started for all applicants",
            status=RevalidateStatus.RUNNING,
        )
        assert "all applicants" in resp.message
        assert resp.status == RevalidateStatus.RUNNING

    def test_revalidate_response_with_days_filter(self) -> None:
        """Should include days in message when filtered."""
        resp = RevalidateResponse(
            message="Re-validation started for applicants who applied in the last 30 days",
            status=RevalidateStatus.RUNNING,
        )
        assert "30 days" in resp.message


class TestRevalidateRoutesEndpoints:
    """Tests for revalidate API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with revalidate router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_get_revalidate_status_returns_current_state(self, app: FastAPI) -> None:
        """Should return current re-validation state."""
        # Reset global state
        _revalidate_state.status = RevalidateStatus.IDLE
        _revalidate_state.progress = 0
        _revalidate_state.total = 0
        _revalidate_state.message = ""
        _revalidate_state.last_run_at = None
        _revalidate_state.error = None
        _revalidate_state.applicants_processed = 0
        _revalidate_state.flags_raised = 0
        _revalidate_state.flags_cleared = 0
        _revalidate_state.risk_level_changes = 0
        _revalidate_state.current_applicant_name = None

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/revalidate/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["progress"] == 0
        assert data["total"] == 0
        assert data["applicants_processed"] == 0

    @pytest.mark.asyncio
    async def test_get_revalidate_status_shows_running(self, app: FastAPI) -> None:
        """Should show running status during re-validation."""
        _revalidate_state.status = RevalidateStatus.RUNNING
        _revalidate_state.progress = 50
        _revalidate_state.total = 100
        _revalidate_state.message = "Re-validating applicants..."
        _revalidate_state.current_applicant_name = "Jane Doe"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/revalidate/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["current_applicant_name"] == "Jane Doe"

        # Reset state
        _revalidate_state.status = RevalidateStatus.IDLE

    @pytest.mark.asyncio
    async def test_get_revalidate_status_shows_completed(self, app: FastAPI) -> None:
        """Should show completed status with statistics."""
        _revalidate_state.status = RevalidateStatus.COMPLETED
        _revalidate_state.progress = 100
        _revalidate_state.total = 100
        _revalidate_state.message = "Re-validation complete"
        _revalidate_state.last_run_at = datetime.now(UTC)
        _revalidate_state.applicants_processed = 100
        _revalidate_state.flags_raised = 45
        _revalidate_state.flags_cleared = 30
        _revalidate_state.risk_level_changes = 15

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/revalidate/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["applicants_processed"] == 100
        assert data["flags_raised"] == 45
        assert data["flags_cleared"] == 30
        assert data["risk_level_changes"] == 15

        # Reset state
        _revalidate_state.status = RevalidateStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_revalidation_when_idle(self, app: FastAPI) -> None:
        """Should start re-validation and return running status."""
        _revalidate_state.status = RevalidateStatus.IDLE

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/revalidate/start",
                json={},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "all applicants" in data["message"]

        # Reset state
        _revalidate_state.status = RevalidateStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_revalidation_with_days_filter(self, app: FastAPI) -> None:
        """Should accept days filter parameter."""
        _revalidate_state.status = RevalidateStatus.IDLE

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/revalidate/start",
                json={"days": 30},
            )

        assert response.status_code == 200
        data = response.json()
        assert "30 days" in data["message"]

        # Reset state
        _revalidate_state.status = RevalidateStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_revalidation_rejects_when_running(self, app: FastAPI) -> None:
        """Should reject re-validation request when already running."""
        _revalidate_state.status = RevalidateStatus.RUNNING

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/revalidate/start",
                json={},
            )

        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"].lower()

        # Reset state
        _revalidate_state.status = RevalidateStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_revalidation_validation_invalid_days(self, app: FastAPI) -> None:
        """Should reject invalid days value."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/revalidate/start",
                json={"days": 500},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_revalidation_with_clear_flags_false(self, app: FastAPI) -> None:
        """Should accept clear_existing_flags=False."""
        _revalidate_state.status = RevalidateStatus.IDLE

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/revalidate/start",
                json={"clear_existing_flags": False},
            )

        assert response.status_code == 200

        # Reset state
        _revalidate_state.status = RevalidateStatus.IDLE


class TestPerformRevalidationFunction:
    """Tests for _perform_revalidation background task function."""

    @pytest.mark.asyncio
    async def test_handles_empty_applicants(self) -> None:
        """Should complete gracefully when no applicants match filter."""
        with patch("applicant_validator.api.routes.revalidate.get_session") as mock_session:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            # Reset state
            _revalidate_state.status = RevalidateStatus.IDLE

            await _perform_revalidation(days=1)

            assert _revalidate_state.status == RevalidateStatus.COMPLETED
            assert "No applicants found" in _revalidate_state.message

    @pytest.mark.asyncio
    async def test_updates_state_on_failure(self) -> None:
        """Should update state with error on failure."""
        with patch("applicant_validator.api.routes.revalidate.get_session") as mock_session:
            mock_session.return_value.__aenter__.side_effect = Exception(
                "Database connection failed"
            )
            mock_session.return_value.__aexit__.return_value = None

            _revalidate_state.status = RevalidateStatus.IDLE

            await _perform_revalidation()

            assert _revalidate_state.status == RevalidateStatus.FAILED
            assert "Database connection failed" in _revalidate_state.error
            assert _revalidate_state.current_applicant_name is None
