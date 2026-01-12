"""Tests for applicants API routes."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.applicants import (
    _applicant_to_list_response,
    _applicant_to_response,
    _flag_to_response,
    _posting_to_response,
    router,
)
from applicant_validator.api.schemas.applicants import (
    ApplicantListResponse,
    ApplicantResponse,
    ApplicantUpdateRequest,
    FlagResponse,
    FlagTypeListResponse,
    FlagTypeResponse,
    PaginatedApplicantsResponse,
    PostingResponse,
    RiskLevelListResponse,
    SourceListResponse,
    TAListResponse,
    ValidateApplicantResponse,
)


class TestFlagToResponseHelper:
    """Tests for _flag_to_response helper function."""

    def test_converts_flag_to_response(self) -> None:
        """Should convert Flag model to FlagResponse."""
        flag = MagicMock()
        flag.id = uuid.uuid4()
        flag.flag_type = MagicMock()
        flag.flag_type.code = "DISPOSABLE_EMAIL"
        flag.flag_type.name = "Disposable Email"
        flag.flag_type.category = "email"
        flag.severity = "high"
        flag.message = "Email domain is disposable"
        flag.is_active = True
        flag.created_at = datetime.now(UTC)

        result = _flag_to_response(flag)

        assert isinstance(result, FlagResponse)
        assert result.flag_type_code == "DISPOSABLE_EMAIL"
        assert result.flag_type_name == "Disposable Email"
        assert result.category == "email"
        assert result.severity == "high"
        assert result.message == "Email domain is disposable"
        assert result.is_active is True


class TestPostingToResponseHelper:
    """Tests for _posting_to_response helper function."""

    def test_converts_posting_to_response(self) -> None:
        """Should convert ApplicantPosting to PostingResponse."""
        applicant_posting = MagicMock()
        applicant_posting.posting = MagicMock()
        applicant_posting.posting.id = uuid.uuid4()
        applicant_posting.posting.lever_posting_id = "lever123"
        applicant_posting.posting.title = "Software Engineer"
        applicant_posting.posting.team = "Engineering"
        applicant_posting.posting.department = "Product"
        applicant_posting.posting.location = "Remote"
        applicant_posting.posting.commitment = "Full-time"
        applicant_posting.posting.state = "published"

        result = _posting_to_response(applicant_posting)

        assert isinstance(result, PostingResponse)
        assert result.lever_posting_id == "lever123"
        assert result.title == "Software Engineer"
        assert result.team == "Engineering"
        assert result.department == "Product"
        assert result.location == "Remote"


class TestApplicantToListResponseHelper:
    """Tests for _applicant_to_list_response helper function."""

    def test_converts_applicant_to_list_response(self) -> None:
        """Should convert Applicant to ApplicantListResponse."""
        applicant = MagicMock()
        applicant.id = uuid.uuid4()
        applicant.lever_id = "lever123"
        applicant.name = "John Doe"
        applicant.email = "john@example.com"
        applicant.phone = "+1-555-1234"
        applicant.location = "San Francisco"
        applicant.risk_level = "medium"
        applicant.flag_count = 2
        applicant.opportunity_count = 1
        applicant.is_reviewed = False
        applicant.reviewed_at = None
        applicant.created_at = datetime.now(UTC)
        applicant.lever_created_at = datetime.now(UTC)
        applicant.lever_owner_name = "Jane Recruiter"

        # Mock flags and sources
        flag1 = MagicMock()
        flag1.id = uuid.uuid4()
        flag1.is_active = True
        flag1.flag_type = MagicMock()
        flag1.flag_type.code = "FLAG1"
        flag1.flag_type.name = "Flag One"
        flag1.flag_type.category = "test"
        flag1.severity = "low"
        flag1.message = "Test flag"
        flag1.created_at = datetime.now(UTC)

        flag2 = MagicMock()
        flag2.is_active = False  # Inactive flag should be excluded

        applicant.flags = [flag1, flag2]

        source = MagicMock()
        source.source = "LinkedIn"
        applicant.sources = [source]

        result = _applicant_to_list_response(applicant)

        assert isinstance(result, ApplicantListResponse)
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        assert result.risk_level == "medium"
        assert len(result.flags) == 1  # Only active flags
        assert result.sources == ["LinkedIn"]
        assert result.assigned_ta == "Jane Recruiter"


class TestApplicantToResponseHelper:
    """Tests for _applicant_to_response helper function."""

    def test_converts_applicant_to_full_response(self) -> None:
        """Should convert Applicant to full ApplicantResponse."""
        applicant = MagicMock()
        applicant.id = uuid.uuid4()
        applicant.lever_id = "lever123"
        applicant.name = "John Doe"
        applicant.email = "john@example.com"
        applicant.phone = "+1-555-1234"
        applicant.location = "San Francisco"
        applicant.linkedin_url = "https://linkedin.com/in/johndoe"
        applicant.risk_level = "high"
        applicant.validation_score = 75.5
        applicant.flag_count = 3
        applicant.opportunity_count = 2
        applicant.is_reviewed = True
        applicant.reviewed_at = datetime.now(UTC)
        applicant.reviewed_by = "admin@example.com"
        applicant.created_at = datetime.now(UTC)
        applicant.updated_at = datetime.now(UTC)
        applicant.lever_created_at = datetime.now(UTC)
        applicant.lever_owner_name = "Jane Recruiter"

        applicant.flags = []
        applicant.sources = []
        applicant.postings = []

        result = _applicant_to_response(applicant)

        assert isinstance(result, ApplicantResponse)
        assert result.name == "John Doe"
        assert result.linkedin_url == "https://linkedin.com/in/johndoe"
        assert result.validation_score == 75.5
        assert result.is_reviewed is True
        assert result.reviewed_by == "admin@example.com"


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_flag_response_model(self) -> None:
        """Should create FlagResponse with all fields."""
        resp = FlagResponse(
            id=uuid.uuid4(),
            flag_type_code="TEST_FLAG",
            flag_type_name="Test Flag",
            category="test",
            severity="medium",
            message="Test message",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        assert resp.flag_type_code == "TEST_FLAG"
        assert resp.severity == "medium"
        assert resp.is_active is True

    def test_posting_response_model(self) -> None:
        """Should create PostingResponse with all fields."""
        resp = PostingResponse(
            id=uuid.uuid4(),
            lever_posting_id="lever123",
            title="Software Engineer",
            team="Engineering",
            department="Product",
            location="Remote",
            commitment="Full-time",
            state="published",
        )
        assert resp.title == "Software Engineer"
        assert resp.team == "Engineering"

    def test_posting_response_optional_fields(self) -> None:
        """Should allow optional fields to be None."""
        resp = PostingResponse(
            id=uuid.uuid4(),
            lever_posting_id="lever123",
            title="Software Engineer",
        )
        assert resp.team is None
        assert resp.department is None
        assert resp.location is None

    def test_applicant_update_request_valid(self) -> None:
        """Should create ApplicantUpdateRequest with valid data."""
        req = ApplicantUpdateRequest(
            is_reviewed=True,
            reviewed_by="admin@example.com",
        )
        assert req.is_reviewed is True
        assert req.reviewed_by == "admin@example.com"

    def test_applicant_update_request_partial(self) -> None:
        """Should allow partial updates."""
        req = ApplicantUpdateRequest(is_reviewed=True)
        assert req.is_reviewed is True
        assert req.reviewed_by is None

    def test_applicant_update_request_empty(self) -> None:
        """Should allow empty update request."""
        req = ApplicantUpdateRequest()
        assert req.is_reviewed is None
        assert req.reviewed_by is None

    def test_ta_list_response_model(self) -> None:
        """Should create TAListResponse with list of TAs."""
        resp = TAListResponse(tas=["Jane Recruiter", "John HR"])
        assert len(resp.tas) == 2
        assert "Jane Recruiter" in resp.tas

    def test_ta_list_response_empty(self) -> None:
        """Should allow empty TAs list."""
        resp = TAListResponse()
        assert resp.tas == []

    def test_source_list_response_model(self) -> None:
        """Should create SourceListResponse with list of sources."""
        resp = SourceListResponse(sources=["LinkedIn", "Referral", "Job Board"])
        assert len(resp.sources) == 3
        assert "LinkedIn" in resp.sources

    def test_flag_type_response_model(self) -> None:
        """Should create FlagTypeResponse with all fields."""
        resp = FlagTypeResponse(
            code="DISPOSABLE_EMAIL",
            name="Disposable Email",
            category="email",
        )
        assert resp.code == "DISPOSABLE_EMAIL"
        assert resp.name == "Disposable Email"
        assert resp.category == "email"

    def test_flag_type_list_response_model(self) -> None:
        """Should create FlagTypeListResponse with list of flag types."""
        resp = FlagTypeListResponse(
            flag_types=[
                FlagTypeResponse(code="FLAG1", name="Flag One", category="cat1"),
                FlagTypeResponse(code="FLAG2", name="Flag Two", category="cat2"),
            ]
        )
        assert len(resp.flag_types) == 2

    def test_risk_level_list_response_model(self) -> None:
        """Should create RiskLevelListResponse with list of levels."""
        resp = RiskLevelListResponse(risk_levels=["low", "medium", "high", "critical"])
        assert len(resp.risk_levels) == 4
        assert "high" in resp.risk_levels

    def test_paginated_applicants_response_model(self) -> None:
        """Should create PaginatedApplicantsResponse with pagination info."""
        resp = PaginatedApplicantsResponse(
            items=[],
            total=100,
            page=2,
            page_size=20,
            total_pages=5,
        )
        assert resp.total == 100
        assert resp.page == 2
        assert resp.page_size == 20
        assert resp.total_pages == 5

    def test_validate_applicant_response_model(self) -> None:
        """Should create ValidateApplicantResponse with validation results."""
        applicant_resp = ApplicantResponse(
            id=uuid.uuid4(),
            lever_id="lever123",
            name="John Doe",
            email="john@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        resp = ValidateApplicantResponse(
            applicant=applicant_resp,
            rules_passed=8,
            rules_failed=2,
            rules_skipped=1,
            flags_raised=2,
            previous_risk_level=None,
            new_risk_level="medium",
            message="Validation complete. 2 issues flagged.",
        )
        assert resp.rules_passed == 8
        assert resp.rules_failed == 2
        assert resp.flags_raised == 2
        assert resp.new_risk_level == "medium"


class TestApplicantsRoutesEndpoints:
    """Tests for applicants API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with applicants router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_list_applicants_invalid_page_size(self, app: FastAPI) -> None:
        """Should reject page_size > 100."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/applicants",
                params={"page_size": 200},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_applicants_invalid_page(self, app: FastAPI) -> None:
        """Should reject page < 1."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/applicants",
                params={"page": 0},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_applicant_invalid_uuid(self, app: FastAPI) -> None:
        """Should return 422 for invalid UUID."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/applicants/invalid-uuid")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_applicant_invalid_uuid(self, app: FastAPI) -> None:
        """Should return 422 for invalid UUID on update."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/applicants/invalid-uuid",
                json={"is_reviewed": True},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_validate_applicant_invalid_uuid(self, app: FastAPI) -> None:
        """Should return 422 for invalid UUID on validate."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/applicants/invalid-uuid/validate")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_tas_endpoint(self, app: FastAPI) -> None:
        """Should return list of assigned TAs."""
        with patch("applicant_validator.api.routes.applicants.get_session") as mock_session:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("Jane Recruiter",), ("John HR",)]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/applicants/tas")

            assert response.status_code == 200
            data = response.json()
            assert "tas" in data
            assert len(data["tas"]) == 2
            assert "Jane Recruiter" in data["tas"]

    @pytest.mark.asyncio
    async def test_list_sources_endpoint(self, app: FastAPI) -> None:
        """Should return list of applicant sources."""
        with patch("applicant_validator.api.routes.applicants.get_session") as mock_session:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("LinkedIn",), ("Referral",)]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/applicants/sources")

            assert response.status_code == 200
            data = response.json()
            assert "sources" in data
            assert "LinkedIn" in data["sources"]

    @pytest.mark.asyncio
    async def test_list_risk_levels_endpoint(self, app: FastAPI) -> None:
        """Should return list of risk levels."""
        with patch("applicant_validator.api.routes.applicants.get_session") as mock_session:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [("low",), ("medium",), ("high",)]
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/applicants/risk-levels")

            assert response.status_code == 200
            data = response.json()
            assert "risk_levels" in data
            assert "high" in data["risk_levels"]
