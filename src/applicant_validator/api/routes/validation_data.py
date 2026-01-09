"""Validation data management API routes.

Endpoints for managing disposable email domains, VoIP carriers,
and syncing data from external sources.
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from applicant_validator.services.validation_data import get_validation_data_service

router = APIRouter(prefix="/validation-data", tags=["validation-data"])


# =============================================================================
# Request/Response Models
# =============================================================================


class DisposableDomainResponse(BaseModel):
    """Response for a single disposable domain."""

    domain: str
    source: str
    is_active: bool


class DisposableDomainListResponse(BaseModel):
    """Response with list of disposable domains."""

    domains: list[str]
    total: int


class AddDomainRequest(BaseModel):
    """Request to add a custom disposable domain."""

    domain: str = Field(..., min_length=3, description="Domain to add (e.g., 'example.com')")
    notes: str | None = Field(
        default=None, description="Optional notes about why this domain was added"
    )


class AddDomainResponse(BaseModel):
    """Response after adding a domain."""

    domain: str
    status: str


class RemoveDomainRequest(BaseModel):
    """Request to deactivate a domain."""

    domain: str = Field(..., min_length=3, description="Domain to deactivate")


class VoIPCarrierResponse(BaseModel):
    """Response for a single VoIP carrier."""

    id: str
    name: str
    match_type: str
    confidence: str


class VoIPCarrierListResponse(BaseModel):
    """Response with list of VoIP carriers."""

    carriers: list[VoIPCarrierResponse]
    total: int


class AddVoIPCarrierRequest(BaseModel):
    """Request to add a VoIP carrier pattern."""

    name: str = Field(..., min_length=1, description="Carrier name or pattern")
    match_type: str = Field(
        default="substring",
        description="Match type: exact, substring, or regex",
    )
    confidence: str = Field(
        default="high",
        description="Confidence level: high, medium, or low",
    )
    notes: str | None = Field(default=None, description="Optional notes")


class VoIPAreaCodeListResponse(BaseModel):
    """Response with list of VoIP area codes."""

    area_codes: list[str]
    total: int


class SyncResponse(BaseModel):
    """Response from a sync operation."""

    status: str
    source: str | None = None
    records_processed: int | None = None
    sync_id: str | None = None
    message: str | None = None


class SyncStatusResponse(BaseModel):
    """Response with sync status info."""

    data_type: str
    last_sync: dict[str, str | int | None] | None
    domain_count: int


class SeedResponse(BaseModel):
    """Response from a seed operation."""

    status: str
    carriers_added: int | None = None
    area_codes_added: int | None = None


# =============================================================================
# Disposable Domains Endpoints
# =============================================================================


@router.get("/disposable-domains", response_model=DisposableDomainListResponse)
async def list_disposable_domains(
    limit: int = 100,
    offset: int = 0,
) -> DisposableDomainListResponse:
    """List disposable email domains.

    Returns a paginated list of known disposable email domains.
    """
    service = get_validation_data_service()
    domains = await service.get_disposable_domains()

    # Simple pagination
    domain_list = sorted(list(domains))
    paginated = domain_list[offset : offset + limit]

    return DisposableDomainListResponse(
        domains=paginated,
        total=len(domains),
    )


@router.post("/disposable-domains", response_model=AddDomainResponse)
async def add_disposable_domain(request: AddDomainRequest) -> AddDomainResponse:
    """Add a custom disposable email domain.

    Adds a domain to the database. If the domain already exists,
    it will be reactivated and updated.
    """
    service = get_validation_data_service()
    result = await service.add_custom_domain(request.domain, request.notes)
    return AddDomainResponse(**result)


@router.delete("/disposable-domains/{domain}", response_model=AddDomainResponse)
async def remove_disposable_domain(domain: str) -> AddDomainResponse:
    """Deactivate a disposable email domain.

    Soft-deletes the domain by marking it as inactive.
    """
    service = get_validation_data_service()
    result = await service.remove_domain(domain)
    return AddDomainResponse(**result)


@router.post("/disposable-domains/sync", response_model=SyncResponse)
async def sync_disposable_domains(
    background_tasks: BackgroundTasks,
    source: str = "disposable-email-domains",
) -> SyncResponse:
    """Sync disposable domains from an external source.

    Fetches the latest list from the specified source and updates
    the database. Runs in the background.

    Available sources:
    - disposable-email-domains: GitHub disposable-email-domains list
    """
    service = get_validation_data_service()

    # Start sync in background
    background_tasks.add_task(service.sync_disposable_domains, source)

    return SyncResponse(
        status="started",
        source=source,
        message="Sync started in background. Check status endpoint for progress.",
    )


@router.get("/disposable-domains/status", response_model=SyncStatusResponse)
async def get_disposable_domains_status() -> SyncStatusResponse:
    """Get status of disposable domains data.

    Returns information about the last sync and current domain count.
    """
    service = get_validation_data_service()
    last_sync = await service.get_last_sync("disposable_domains")
    domain_count = await service.get_domain_count()

    return SyncStatusResponse(
        data_type="disposable_domains",
        last_sync=last_sync,
        domain_count=domain_count,
    )


# =============================================================================
# VoIP Carriers Endpoints
# =============================================================================


@router.get("/voip-carriers", response_model=VoIPCarrierListResponse)
async def list_voip_carriers() -> VoIPCarrierListResponse:
    """List known VoIP carrier patterns.

    Returns all active VoIP carrier patterns used for detection.
    """
    service = get_validation_data_service()
    carriers = await service.get_voip_carriers()

    return VoIPCarrierListResponse(
        carriers=[VoIPCarrierResponse(**c) for c in carriers],
        total=len(carriers),
    )


@router.post("/voip-carriers", response_model=AddDomainResponse)
async def add_voip_carrier(request: AddVoIPCarrierRequest) -> AddDomainResponse:
    """Add a VoIP carrier pattern.

    Adds a carrier name/pattern to detect VoIP numbers.
    """
    service = get_validation_data_service()
    result = await service.add_voip_carrier(
        name=request.name,
        match_type=request.match_type,
        confidence=request.confidence,
        notes=request.notes,
    )
    return AddDomainResponse(domain=result["name"], status=result["status"])


@router.post("/voip-carriers/seed", response_model=SeedResponse)
async def seed_voip_carriers() -> SeedResponse:
    """Seed VoIP carriers with default values.

    Populates the database with a default set of known VoIP carriers.
    Safe to run multiple times - won't duplicate entries.
    """
    service = get_validation_data_service()
    result = await service.seed_voip_carriers()
    return SeedResponse(**result)


# =============================================================================
# VoIP Area Codes Endpoints
# =============================================================================


@router.get("/voip-area-codes", response_model=VoIPAreaCodeListResponse)
async def list_voip_area_codes() -> VoIPAreaCodeListResponse:
    """List known VoIP area codes.

    Returns all active area codes commonly used by VoIP services.
    """
    service = get_validation_data_service()
    codes = await service.get_voip_area_codes()

    return VoIPAreaCodeListResponse(
        area_codes=sorted(list(codes)),
        total=len(codes),
    )


@router.post("/voip-area-codes/seed", response_model=SeedResponse)
async def seed_voip_area_codes() -> SeedResponse:
    """Seed VoIP area codes with default values.

    Populates the database with known VoIP area codes.
    Safe to run multiple times - won't duplicate entries.
    """
    service = get_validation_data_service()
    result = await service.seed_voip_area_codes()
    return SeedResponse(**result)


# =============================================================================
# Combined Seed/Sync Endpoints
# =============================================================================


@router.post("/seed-all", response_model=dict[str, str | dict[str, str | int | None]])
async def seed_all_validation_data() -> dict[str, str | dict[str, str | int | None]]:
    """Seed all validation data with defaults.

    Populates VoIP carriers and area codes with default values.
    For disposable domains, use the sync endpoint to fetch from
    external sources.
    """
    service = get_validation_data_service()

    carriers_result = await service.seed_voip_carriers()
    area_codes_result = await service.seed_voip_area_codes()

    return {
        "status": "completed",
        "voip_carriers": carriers_result,
        "voip_area_codes": area_codes_result,
    }
