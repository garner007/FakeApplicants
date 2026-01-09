"""Lever sync API routes."""

import time
from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from applicant_validator.clients.lever import LeverClient
from applicant_validator.config import get_settings
from applicant_validator.database import Applicant, ApplicantSource, get_session
from applicant_validator.services.integration_settings import get_integration_settings_service
from applicant_validator.services.validation import ensure_flag_types, validate_applicant

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncStatus(str, Enum):
    """Status of a sync operation."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncState:
    """Global sync state tracker."""

    status: SyncStatus = SyncStatus.IDLE
    progress: int = 0
    total: int = 0
    message: str = ""
    last_sync_at: datetime | None = None
    last_sync_count: int = 0
    error: str | None = None


# Global sync state
_sync_state = SyncState()


class SyncRequest(BaseModel):
    """Request to start a sync operation."""

    days: int = Field(default=7, ge=1, le=365, description="Number of days to sync")


class SyncStatusResponse(BaseModel):
    """Response with current sync status."""

    status: SyncStatus
    progress: int
    total: int
    message: str
    last_sync_at: datetime | None
    last_sync_count: int
    error: str | None = None


class SyncResponse(BaseModel):
    """Response after starting a sync."""

    message: str
    status: SyncStatus


class ApplicantCountResponse(BaseModel):
    """Response with applicant count."""

    count: int


async def _perform_sync(days: int) -> None:
    """Perform the actual sync operation."""
    try:
        _sync_state.status = SyncStatus.RUNNING
        _sync_state.progress = 0
        _sync_state.total = 0
        _sync_state.message = "Connecting to Lever API..."
        _sync_state.error = None

        # Get Lever credentials - try database first, then fall back to environment
        api_key = None
        environment = "sandbox"

        async with get_session() as session:
            service = await get_integration_settings_service(session)
            lever_integration = await service.get_integration("lever")

            if lever_integration and lever_integration.api_key and lever_integration.is_enabled:
                api_key = lever_integration.api_key
                # Check config_json for environment setting
                if lever_integration.config_json:
                    import json

                    try:
                        config = json.loads(lever_integration.config_json)
                        environment = config.get("environment", "sandbox")
                    except json.JSONDecodeError:
                        pass

        # Fall back to environment variable if database key not configured
        if not api_key:
            settings = get_settings()
            api_key = settings.lever_api_key
            environment = settings.lever_environment

        if not api_key:
            raise ValueError(
                "Lever API key not configured. "
                "Add it in Integration Settings or set LEVER_API_KEY environment variable."
            )

        client = LeverClient(
            api_key=api_key,
            environment=environment,
        )

        # Calculate timestamp for date filter
        created_at_start = int((time.time() - days * 24 * 60 * 60) * 1000)

        # Fetch all applicants
        all_applicants = []
        offset = None
        page = 1

        async with client:
            while True:
                _sync_state.message = f"Fetching page {page} from Lever..."

                params: dict[str, int | str] = {"limit": 100, "created_at_start": created_at_start}
                if offset:
                    params["offset"] = offset

                response = await client._make_lever_request("GET", "/candidates", params=params)

                candidates = response.get("data", [])
                if not candidates:
                    break

                all_applicants.extend(candidates)
                _sync_state.total = len(all_applicants)

                if response.get("hasNext"):
                    offset = response.get("next")
                    page += 1
                else:
                    break

        if not all_applicants:
            _sync_state.status = SyncStatus.COMPLETED
            _sync_state.message = "No applicants found in the specified date range"
            _sync_state.last_sync_at = datetime.now(UTC)
            _sync_state.last_sync_count = 0
            return

        # Fetch all users from Lever to map owner IDs to names
        _sync_state.message = "Fetching user list from Lever..."
        user_map: dict[str, str] = {}
        async with client:
            try:
                users_response = await client._make_lever_request("GET", "/users")
                users_data = users_response.get("data", [])
                for user in users_data:
                    user_id = user.get("id")
                    user_name = user.get("name")
                    if user_id and user_name:
                        user_map[user_id] = user_name
            except Exception:
                # If fetching users fails, continue without owner names
                pass

        # Upsert applicants (insert new, update existing)
        _sync_state.message = "Syncing applicants..."
        applicants_to_validate: list[Applicant] = []
        new_count = 0
        updated_count = 0

        async with get_session() as session:
            # Build a set of lever_ids we're syncing for efficient lookup
            lever_ids = [data["id"] for data in all_applicants]

            # Fetch existing applicants in batches to avoid PostgreSQL's 32767 param limit
            existing_applicants: dict[str, Applicant] = {}
            BATCH_SIZE = 30000
            for i in range(0, len(lever_ids), BATCH_SIZE):
                batch_ids = lever_ids[i : i + BATCH_SIZE]
                result = await session.execute(
                    select(Applicant).where(Applicant.lever_id.in_(batch_ids))
                )
                for applicant in result.scalars().all():
                    existing_applicants[applicant.lever_id] = applicant

            for i, data in enumerate(all_applicants, 1):
                # Extract data from Lever
                emails = data.get("emails", [])
                sources = data.get("sources", [])

                # Detect if this applicant was manually added
                is_manually_added = "Added manually" in sources

                # Handle missing email - use placeholder for manually added applicants
                if emails:
                    email = emails[0]
                elif is_manually_added:
                    email = "(not provided - manually added)"
                else:
                    email = "(not provided)"

                phones = data.get("phones", [])
                phone = phones[0].get("value") if phones else None

                links = data.get("links", [])
                linkedin_url = None
                for link in links:
                    if "linkedin.com" in link.lower():
                        linkedin_url = link
                        break

                created_at_ms = data.get("createdAt", 0)
                lever_created_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)

                opportunity_ids = data.get("opportunityIds", [])
                opportunity_id = opportunity_ids[0] if opportunity_ids else None

                stage_changes = data.get("stageChanges", [])
                stage = stage_changes[-1].get("toStageId") if stage_changes else None

                # Extract owner info - try owner first, then followers as fallback
                lever_owner_id = data.get("owner")
                lever_owner_name = user_map.get(lever_owner_id) if lever_owner_id else None

                # If owner doesn't resolve to a name, check followers
                if not lever_owner_name:
                    followers = data.get("followers", [])
                    for follower_id in followers:
                        if follower_id in user_map:
                            lever_owner_id = follower_id
                            lever_owner_name = user_map[follower_id]
                            break

                lever_id = data["id"]
                existing = existing_applicants.get(lever_id)

                if existing:
                    # UPDATE existing applicant - preserve user fields
                    needs_revalidation = existing.email != email or existing.phone != phone

                    # Update Lever-sourced fields only
                    existing.name = data.get("name", "Unknown")
                    existing.email = email
                    existing.phone = phone
                    existing.location = data.get("location")
                    existing.headline = data.get("headline")
                    existing.linkedin_url = linkedin_url
                    existing.lever_opportunity_id = opportunity_id
                    existing.lever_stage = stage
                    existing.lever_created_at = lever_created_at
                    existing.lever_owner_id = lever_owner_id
                    existing.lever_owner_name = lever_owner_name
                    existing.is_manually_added = is_manually_added
                    # Preserve: is_reviewed, reviewed_by, reviewed_at, risk_level, flag_count

                    # Update sources - delete old, add new
                    await session.execute(
                        delete(ApplicantSource).where(ApplicantSource.applicant_id == existing.id)
                    )
                    for source in sources:
                        source_record = ApplicantSource(
                            applicant_id=existing.id,
                            source=source,
                        )
                        session.add(source_record)

                    if needs_revalidation:
                        applicants_to_validate.append(existing)

                    updated_count += 1
                else:
                    # INSERT new applicant
                    applicant = Applicant(
                        lever_id=lever_id,
                        lever_opportunity_id=opportunity_id,
                        name=data.get("name", "Unknown"),
                        email=email,
                        phone=phone,
                        location=data.get("location"),
                        headline=data.get("headline"),
                        linkedin_url=linkedin_url,
                        lever_stage=stage,
                        lever_created_at=lever_created_at,
                        lever_owner_id=lever_owner_id,
                        lever_owner_name=lever_owner_name,
                        risk_level=None,
                        validation_score=None,
                        flag_count=0,
                        is_reviewed=False,
                        is_manually_added=is_manually_added,
                    )
                    session.add(applicant)
                    await session.flush()

                    # Add sources
                    for source in sources:
                        source_record = ApplicantSource(
                            applicant_id=applicant.id,
                            source=source,
                        )
                        session.add(source_record)

                    applicants_to_validate.append(applicant)
                    new_count += 1

                _sync_state.progress = i
                if i % 100 == 0:
                    _sync_state.message = f"Processed {i}/{len(all_applicants)} applicants..."
                    await session.flush()

            await session.commit()

        # Run validation only on new or changed applicants
        if applicants_to_validate:
            _sync_state.message = f"Validating {len(applicants_to_validate)} applicants..."
            _sync_state.progress = 0
            _sync_state.total = len(applicants_to_validate)

            async with get_session() as session:
                # Ensure flag types exist first
                flag_types = await ensure_flag_types(session)
                await session.commit()

                # Re-fetch applicants in this session and validate
                for i, applicant in enumerate(applicants_to_validate, 1):
                    # Fetch the applicant in this session
                    result = await session.execute(
                        select(Applicant).where(Applicant.id == applicant.id)
                    )
                    db_applicant = result.scalar_one_or_none()

                    if db_applicant:
                        await validate_applicant(session, db_applicant, flag_types, "sync")

                    _sync_state.progress = i
                    if i % 100 == 0:
                        _sync_state.message = (
                            f"Validated {i}/{len(applicants_to_validate)} applicants..."
                        )
                        await session.commit()

                await session.commit()

        _sync_state.status = SyncStatus.COMPLETED
        _sync_state.message = (
            f"Sync complete: {new_count} new, {updated_count} updated, "
            f"{len(applicants_to_validate)} validated"
        )
        _sync_state.last_sync_at = datetime.now(UTC)
        _sync_state.last_sync_count = len(all_applicants)

    except Exception as e:
        _sync_state.status = SyncStatus.FAILED
        _sync_state.error = str(e)
        _sync_state.message = f"Sync failed: {e!s}"


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status() -> SyncStatusResponse:
    """Get the current sync status."""
    return SyncStatusResponse(
        status=_sync_state.status,
        progress=_sync_state.progress,
        total=_sync_state.total,
        message=_sync_state.message,
        last_sync_at=_sync_state.last_sync_at,
        last_sync_count=_sync_state.last_sync_count,
        error=_sync_state.error,
    )


@router.post("/start", response_model=SyncResponse)
async def start_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
) -> SyncResponse:
    """Start a sync operation from Lever."""
    if _sync_state.status == SyncStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    # Reset state and start sync in background
    _sync_state.status = SyncStatus.RUNNING
    _sync_state.progress = 0
    _sync_state.total = 0
    _sync_state.message = "Starting sync..."
    _sync_state.error = None

    background_tasks.add_task(_perform_sync, request.days)

    return SyncResponse(
        message=f"Sync started for last {request.days} days",
        status=SyncStatus.RUNNING,
    )


@router.get("/count", response_model=ApplicantCountResponse)
async def get_applicant_count() -> ApplicantCountResponse:
    """Get the current count of applicants in the database."""
    async with get_session() as session:
        result = await session.execute(
            select(func.count(Applicant.id)).where(Applicant.is_deleted == False)  # noqa: E712
        )
        count = result.scalar() or 0
        return ApplicantCountResponse(count=count)
