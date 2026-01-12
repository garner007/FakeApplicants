"""Tests for validation_data API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.validation_data import (
    AddDomainRequest,
    AddDomainResponse,
    AddVoIPCarrierRequest,
    DisposableDomainListResponse,
    RemoveDomainRequest,
    SeedResponse,
    SyncResponse,
    SyncStatusResponse,
    VoIPAreaCodeListResponse,
    VoIPCarrierListResponse,
    VoIPCarrierResponse,
    router,
)


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_disposable_domain_list_response_model(self) -> None:
        """Should create DisposableDomainListResponse with domains and total."""
        resp = DisposableDomainListResponse(
            domains=["mailinator.com", "tempmail.com", "guerrillamail.com"],
            total=3,
        )
        assert len(resp.domains) == 3
        assert resp.total == 3
        assert "mailinator.com" in resp.domains

    def test_disposable_domain_list_response_empty(self) -> None:
        """Should handle empty domains list."""
        resp = DisposableDomainListResponse(domains=[], total=0)
        assert resp.domains == []
        assert resp.total == 0

    def test_add_domain_request_valid(self) -> None:
        """Should create AddDomainRequest with domain."""
        req = AddDomainRequest(domain="tempmail.com", notes="Added for testing")
        assert req.domain == "tempmail.com"
        assert req.notes == "Added for testing"

    def test_add_domain_request_min_length(self) -> None:
        """Should require domain min length of 3."""
        with pytest.raises(ValueError):
            AddDomainRequest(domain="ab")

    def test_add_domain_request_optional_notes(self) -> None:
        """Should allow notes to be None."""
        req = AddDomainRequest(domain="spam.com")
        assert req.notes is None

    def test_add_domain_response_model(self) -> None:
        """Should create AddDomainResponse with domain and status."""
        resp = AddDomainResponse(domain="tempmail.com", status="added")
        assert resp.domain == "tempmail.com"
        assert resp.status == "added"

    def test_remove_domain_request_valid(self) -> None:
        """Should create RemoveDomainRequest with domain."""
        req = RemoveDomainRequest(domain="tempmail.com")
        assert req.domain == "tempmail.com"

    def test_voip_carrier_response_model(self) -> None:
        """Should create VoIPCarrierResponse with all fields."""
        resp = VoIPCarrierResponse(
            id="carrier123",
            name="Google Voice",
            match_type="substring",
            confidence="high",
        )
        assert resp.id == "carrier123"
        assert resp.name == "Google Voice"
        assert resp.match_type == "substring"
        assert resp.confidence == "high"

    def test_voip_carrier_list_response_model(self) -> None:
        """Should create VoIPCarrierListResponse with carriers."""
        carriers = [
            VoIPCarrierResponse(
                id="1", name="Google Voice", match_type="substring", confidence="high"
            ),
            VoIPCarrierResponse(id="2", name="Twilio", match_type="exact", confidence="high"),
        ]
        resp = VoIPCarrierListResponse(carriers=carriers, total=2)
        assert len(resp.carriers) == 2
        assert resp.total == 2

    def test_add_voip_carrier_request_valid(self) -> None:
        """Should create AddVoIPCarrierRequest with all fields."""
        req = AddVoIPCarrierRequest(
            name="New Carrier",
            match_type="regex",
            confidence="medium",
            notes="Added for testing",
        )
        assert req.name == "New Carrier"
        assert req.match_type == "regex"
        assert req.confidence == "medium"
        assert req.notes == "Added for testing"

    def test_add_voip_carrier_request_defaults(self) -> None:
        """Should use default values."""
        req = AddVoIPCarrierRequest(name="Test Carrier")
        assert req.match_type == "substring"
        assert req.confidence == "high"
        assert req.notes is None

    def test_voip_area_code_list_response_model(self) -> None:
        """Should create VoIPAreaCodeListResponse with area codes."""
        resp = VoIPAreaCodeListResponse(area_codes=["500", "533", "544"], total=3)
        assert len(resp.area_codes) == 3
        assert resp.total == 3
        assert "500" in resp.area_codes

    def test_sync_response_model(self) -> None:
        """Should create SyncResponse with all fields."""
        resp = SyncResponse(
            status="started",
            source="disposable-email-domains",
            records_processed=None,
            sync_id="sync123",
            message="Sync started in background",
        )
        assert resp.status == "started"
        assert resp.source == "disposable-email-domains"
        assert resp.message == "Sync started in background"

    def test_sync_status_response_model(self) -> None:
        """Should create SyncStatusResponse with all fields."""
        resp = SyncStatusResponse(
            data_type="disposable_domains",
            last_sync={
                "sync_id": "sync123",
                "completed_at": "2024-01-01T00:00:00",
                "records_added": 1000,
            },
            domain_count=5000,
        )
        assert resp.data_type == "disposable_domains"
        assert resp.domain_count == 5000
        assert resp.last_sync["records_added"] == 1000

    def test_sync_status_response_no_last_sync(self) -> None:
        """Should handle null last_sync."""
        resp = SyncStatusResponse(
            data_type="disposable_domains",
            last_sync=None,
            domain_count=0,
        )
        assert resp.last_sync is None

    def test_seed_response_model(self) -> None:
        """Should create SeedResponse with counts."""
        resp = SeedResponse(
            status="completed",
            carriers_added=15,
            area_codes_added=10,
        )
        assert resp.status == "completed"
        assert resp.carriers_added == 15
        assert resp.area_codes_added == 10


class TestDisposableDomainEndpoints:
    """Tests for disposable domain endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with validation_data router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_list_disposable_domains(self, app: FastAPI) -> None:
        """Should return list of disposable domains."""
        mock_domains = {"mailinator.com", "tempmail.com", "guerrillamail.com"}

        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.get_disposable_domains = AsyncMock(return_value=mock_domains)
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/validation-data/disposable-domains")

            assert response.status_code == 200
            data = response.json()
            assert "domains" in data
            assert "total" in data
            assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_disposable_domains_with_pagination(self, app: FastAPI) -> None:
        """Should paginate domain list."""
        mock_domains = {f"domain{i}.com" for i in range(50)}

        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.get_disposable_domains = AsyncMock(return_value=mock_domains)
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/validation-data/disposable-domains",
                    params={"limit": 10, "offset": 0},
                )

            assert response.status_code == 200
            data = response.json()
            assert len(data["domains"]) == 10
            assert data["total"] == 50

    @pytest.mark.asyncio
    async def test_add_disposable_domain(self, app: FastAPI) -> None:
        """Should add a new disposable domain."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.add_custom_domain = AsyncMock(
                return_value={"domain": "newspam.com", "status": "added"}
            )
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/validation-data/disposable-domains",
                    json={"domain": "newspam.com", "notes": "Added for testing"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["domain"] == "newspam.com"
            assert data["status"] == "added"

    @pytest.mark.asyncio
    async def test_remove_disposable_domain(self, app: FastAPI) -> None:
        """Should remove/deactivate a disposable domain."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.remove_domain = AsyncMock(
                return_value={"domain": "oldspam.com", "status": "deactivated"}
            )
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.delete(
                    "/api/validation-data/disposable-domains/oldspam.com"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deactivated"

    @pytest.mark.asyncio
    async def test_sync_disposable_domains(self, app: FastAPI) -> None:
        """Should start sync in background."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.sync_disposable_domains = AsyncMock()
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/validation-data/disposable-domains/sync",
                    params={"source": "disposable-email-domains"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "background" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_get_disposable_domains_status(self, app: FastAPI) -> None:
        """Should return status of disposable domains data."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.get_last_sync = AsyncMock(
                return_value={
                    "sync_id": "sync123",
                    "completed_at": "2024-01-01T00:00:00",
                    "records_added": 5000,
                }
            )
            mock_service.get_domain_count = AsyncMock(return_value=10000)
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/validation-data/disposable-domains/status")

            assert response.status_code == 200
            data = response.json()
            assert data["data_type"] == "disposable_domains"
            assert data["domain_count"] == 10000


class TestVoIPCarrierEndpoints:
    """Tests for VoIP carrier endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_list_voip_carriers(self, app: FastAPI) -> None:
        """Should return list of VoIP carriers."""
        mock_carriers = [
            {"id": "1", "name": "Google Voice", "match_type": "substring", "confidence": "high"},
            {"id": "2", "name": "Twilio", "match_type": "exact", "confidence": "high"},
        ]

        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.get_voip_carriers = AsyncMock(return_value=mock_carriers)
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/validation-data/voip-carriers")

            assert response.status_code == 200
            data = response.json()
            assert "carriers" in data
            assert "total" in data
            assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_add_voip_carrier(self, app: FastAPI) -> None:
        """Should add a new VoIP carrier."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.add_voip_carrier = AsyncMock(
                return_value={"name": "New Carrier", "status": "added"}
            )
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/validation-data/voip-carriers",
                    json={
                        "name": "New Carrier",
                        "match_type": "substring",
                        "confidence": "high",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "added"

    @pytest.mark.asyncio
    async def test_seed_voip_carriers(self, app: FastAPI) -> None:
        """Should seed VoIP carriers with defaults."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.seed_voip_carriers = AsyncMock(
                return_value={"status": "completed", "carriers_added": 15}
            )
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/api/validation-data/voip-carriers/seed")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["carriers_added"] == 15


class TestVoIPAreaCodeEndpoints:
    """Tests for VoIP area code endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_list_voip_area_codes(self, app: FastAPI) -> None:
        """Should return list of VoIP area codes."""
        mock_codes = {"500", "533", "544", "566", "577"}

        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.get_voip_area_codes = AsyncMock(return_value=mock_codes)
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/validation-data/voip-area-codes")

            assert response.status_code == 200
            data = response.json()
            assert "area_codes" in data
            assert "total" in data
            assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_seed_voip_area_codes(self, app: FastAPI) -> None:
        """Should seed VoIP area codes with defaults."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.seed_voip_area_codes = AsyncMock(
                return_value={"status": "completed", "area_codes_added": 10}
            )
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/api/validation-data/voip-area-codes/seed")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["area_codes_added"] == 10


class TestSeedAllEndpoint:
    """Tests for seed-all endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_seed_all_validation_data(self, app: FastAPI) -> None:
        """Should seed all validation data."""
        with patch(
            "applicant_validator.api.routes.validation_data.get_validation_data_service"
        ) as mock_service_fn:
            mock_service = MagicMock()
            mock_service.seed_voip_carriers = AsyncMock(
                return_value={"status": "completed", "carriers_added": 15}
            )
            mock_service.seed_voip_area_codes = AsyncMock(
                return_value={"status": "completed", "area_codes_added": 10}
            )
            mock_service_fn.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/api/validation-data/seed-all")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert "voip_carriers" in data
            assert "voip_area_codes" in data
