"""Lever sync API routes."""

import re
import time
from datetime import UTC, datetime
from enum import Enum
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from applicant_validator.clients.lever import LeverClient


def sanitize_linkedin_url(url: str) -> str | None:
    """Sanitize a LinkedIn URL by stripping tracking parameters.

    Keeps the URL even if it's not a profile URL (e.g., job postings),
    as non-profile URLs can be used for flagging suspicious applicants.

    Args:
        url: Raw LinkedIn URL.

    Returns:
        Clean LinkedIn URL without query parameters, or None if not LinkedIn.
    """
    try:
        parsed = urlparse(url)

        # Must be linkedin.com domain
        if "linkedin.com" not in parsed.netloc.lower():
            return None

        # Extract just the path, ignoring query parameters
        path = parsed.path.rstrip("/")

        if not path:
            return None

        # Reconstruct clean URL without tracking params
        return f"https://www.linkedin.com{path}"

    except Exception:
        return None


def extract_linkedin_url(links: list[str]) -> str | None:
    """Extract and sanitize LinkedIn URL from list of links.

    Args:
        links: List of URL strings.

    Returns:
        Clean LinkedIn URL if found, None otherwise.
    """
    for link in links:
        if "linkedin.com" in link.lower():
            sanitized = sanitize_linkedin_url(link)
            if sanitized:
                return sanitized
    return None


def is_linkedin_profile_url(url: str | None) -> bool:
    """Check if a LinkedIn URL is a valid profile URL.

    Args:
        url: LinkedIn URL to check.

    Returns:
        True if it's a profile URL (/in/... or /pub/...), False otherwise.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return bool(re.match(r"^/(in|pub)/[^/?]+", path))
    except Exception:
        return False


from applicant_validator.config import get_settings
from applicant_validator.database import (
    Applicant,
    ApplicantPosting,
    ApplicantSource,
    Flag,
    FlagEvidence,
    FlagSeverity,
    FlagType,
    LeverPosting,
    get_session,
)
from applicant_validator.services.integration_settings import get_integration_settings_service
from applicant_validator.services.validation import ensure_flag_types, validate_applicant

# Default threshold for mass applicant detection
DEFAULT_MASS_APPLICANT_THRESHOLD = 5

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
        mass_applicant_threshold = DEFAULT_MASS_APPLICANT_THRESHOLD

        async with get_session() as session:
            service = await get_integration_settings_service(session)
            lever_integration = await service.get_integration("lever")

            if lever_integration and lever_integration.api_key and lever_integration.is_enabled:
                api_key = lever_integration.api_key
                # Check config_json for environment and mass_applicant_threshold settings
                if lever_integration.config_json:
                    import json

                    try:
                        config = json.loads(lever_integration.config_json)
                        environment = config.get("environment", "sandbox")
                        mass_applicant_threshold = config.get(
                            "mass_applicant_threshold", DEFAULT_MASS_APPLICANT_THRESHOLD
                        )
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
                linkedin_url = extract_linkedin_url(links)

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

                # Calculate count fields for mass applicant detection
                opportunity_count = len(data.get("opportunityIds", []))
                email_count = len(data.get("emails", []))
                phone_count = len(data.get("phones", []))

                # Ensure minimum of 1 for each count
                opportunity_count = max(1, opportunity_count)
                email_count = max(1, email_count)
                phone_count = max(1, phone_count)

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
                    existing.opportunity_count = opportunity_count
                    existing.email_count = email_count
                    existing.phone_count = phone_count
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
                        opportunity_count=opportunity_count,
                        email_count=email_count,
                        phone_count=phone_count,
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

        # Sync job postings and link applicants to postings
        _sync_state.message = "Syncing job postings..."

        # Collect all unique opportunity IDs from applicants
        all_opportunity_ids: set[str] = set()
        applicant_opportunity_map: dict[str, list[str]] = {}  # lever_id -> opportunity_ids

        for data in all_applicants:
            opp_ids = data.get("opportunityIds", [])
            lever_id = data["id"]
            if opp_ids:
                all_opportunity_ids.update(opp_ids)
                applicant_opportunity_map[lever_id] = opp_ids

        if all_opportunity_ids:
            # Fetch all postings from Lever
            all_postings: dict[str, dict] = {}  # posting_id -> posting_data
            opp_to_posting: dict[str, str] = {}  # opportunity_id -> posting_id

            async with client:
                # First fetch all postings
                _sync_state.message = "Fetching job postings from Lever..."
                offset = None
                while True:
                    postings = await client.get_postings(limit=100, offset=offset)
                    if not postings:
                        break

                    for posting in postings:
                        posting_id = posting.get("id")
                        if posting_id:
                            all_postings[posting_id] = posting

                    # Check for pagination (Lever uses hasNext)
                    # For postings endpoint, we just keep fetching until empty
                    if len(postings) < 100:
                        break
                    # Use the last posting's id as offset if needed
                    offset = postings[-1].get("id") if postings else None
                    if not offset:
                        break

                # Fetch opportunities to get posting IDs
                _sync_state.message = "Mapping opportunities to postings..."
                for opp_id in all_opportunity_ids:
                    try:
                        opp_data = await client.get_opportunity(opp_id)
                        posting_id = opp_data.get("posting")
                        if posting_id:
                            opp_to_posting[opp_id] = posting_id
                    except Exception:
                        # Skip opportunities that can't be fetched
                        continue

            # Store postings and create applicant links
            _sync_state.message = "Storing job postings..."
            async with get_session() as session:
                # Get existing postings
                existing_posting_ids = set()
                if all_postings:
                    result = await session.execute(
                        select(LeverPosting.lever_posting_id).where(
                            LeverPosting.lever_posting_id.in_(list(all_postings.keys()))
                        )
                    )
                    existing_posting_ids = {row[0] for row in result.fetchall()}

                # Insert new postings
                posting_db_map: dict[str, LeverPosting] = {}  # lever_posting_id -> db record

                for posting_id, posting_data in all_postings.items():
                    if posting_id not in existing_posting_ids:
                        # Parse posting created_at
                        created_at_ms = posting_data.get("createdAt", 0)
                        lever_created_at = (
                            datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)
                            if created_at_ms
                            else None
                        )

                        db_posting = LeverPosting(
                            lever_posting_id=posting_id,
                            title=posting_data.get("text", "Unknown Position"),
                            team=posting_data.get("categories", {}).get("team"),
                            department=posting_data.get("categories", {}).get("department"),
                            location=posting_data.get("categories", {}).get("location"),
                            commitment=posting_data.get("categories", {}).get("commitment"),
                            state=posting_data.get("state"),
                            lever_created_at=lever_created_at,
                        )
                        session.add(db_posting)
                        posting_db_map[posting_id] = db_posting

                await session.flush()

                # Fetch all posting records (including existing ones)
                result = await session.execute(select(LeverPosting))
                for db_posting in result.scalars().all():
                    posting_db_map[db_posting.lever_posting_id] = db_posting

                # Get existing applicant-posting links
                _sync_state.message = "Linking applicants to postings..."

                # Get all applicants by lever_id
                applicant_db_map: dict[str, Applicant] = {}
                lever_ids = list(applicant_opportunity_map.keys())
                if lever_ids:
                    for i in range(0, len(lever_ids), 30000):
                        batch_ids = lever_ids[i : i + 30000]
                        result = await session.execute(
                            select(Applicant).where(Applicant.lever_id.in_(batch_ids))
                        )
                        for applicant in result.scalars().all():
                            applicant_db_map[applicant.lever_id] = applicant

                # Get existing applicant-posting links to avoid duplicates
                existing_links: set[tuple[str, str]] = set()  # (applicant_id, posting_id)
                result = await session.execute(
                    select(
                        ApplicantPosting.applicant_id,
                        ApplicantPosting.posting_id,
                    )
                )
                for row in result.fetchall():
                    existing_links.add((str(row[0]), str(row[1])))

                # Create applicant-posting links
                for lever_id, opp_ids in applicant_opportunity_map.items():
                    applicant = applicant_db_map.get(lever_id)
                    if not applicant:
                        continue

                    for opp_id in opp_ids:
                        posting_id = opp_to_posting.get(opp_id)
                        if not posting_id:
                            continue

                        db_posting = posting_db_map.get(posting_id)
                        if not db_posting:
                            continue

                        # Check if link already exists
                        link_key = (str(applicant.id), str(db_posting.id))
                        if link_key in existing_links:
                            continue

                        # Create the link
                        applicant_posting = ApplicantPosting(
                            applicant_id=applicant.id,
                            posting_id=db_posting.id,
                            lever_opportunity_id=opp_id,
                        )
                        session.add(applicant_posting)
                        existing_links.add(link_key)

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

        # Check for mass applicants and create flags
        mass_applicant_count = 0
        if mass_applicant_threshold > 0:
            _sync_state.message = "Checking for mass applicants..."

            async with get_session() as session:
                # Get or create the MASS_APPLICANT flag type
                flag_type_result = await session.execute(
                    select(FlagType).where(FlagType.code == "MASS_APPLICANT")
                )
                mass_applicant_flag_type = flag_type_result.scalar_one_or_none()

                if not mass_applicant_flag_type:
                    # Create the flag type if it doesn't exist
                    mass_applicant_flag_type = FlagType(
                        code="MASS_APPLICANT",
                        name="Mass Applicant",
                        description="Applicant applied to many positions in a short time",
                        category="behavior",
                        default_severity=FlagSeverity.MEDIUM.value,
                        is_active=True,
                        auto_flag=True,
                        weight=2.0,
                    )
                    session.add(mass_applicant_flag_type)
                    await session.flush()

                # Find applicants that meet the threshold and don't already have this flag
                for applicant in applicants_to_validate:
                    # Re-fetch the applicant to get updated opportunity_count
                    applicant_result = await session.execute(
                        select(Applicant).where(Applicant.id == applicant.id)
                    )
                    db_applicant = applicant_result.scalar_one_or_none()

                    if not db_applicant:
                        continue

                    if db_applicant.opportunity_count >= mass_applicant_threshold:
                        # Check if flag already exists for this applicant
                        existing_flag_result = await session.execute(
                            select(Flag).where(
                                Flag.applicant_id == db_applicant.id,
                                Flag.flag_type_id == mass_applicant_flag_type.id,
                                Flag.is_active == True,  # noqa: E712
                            )
                        )
                        existing_flag = existing_flag_result.scalar_one_or_none()

                        if not existing_flag:
                            # Create the MASS_APPLICANT flag
                            flag = Flag(
                                applicant_id=db_applicant.id,
                                flag_type_id=mass_applicant_flag_type.id,
                                severity=FlagSeverity.MEDIUM.value,
                                message=(
                                    f"Applicant applied to {db_applicant.opportunity_count} "
                                    f"positions (threshold: {mass_applicant_threshold})"
                                ),
                                is_active=True,
                                is_reviewed=False,
                                is_resolved=False,
                            )
                            session.add(flag)
                            await session.flush()

                            # Add evidence
                            evidence = FlagEvidence(
                                flag_id=flag.id,
                                evidence_type="count",
                                key="opportunity_count",
                                value=str(db_applicant.opportunity_count),
                                description=(
                                    f"Number of positions applied to: "
                                    f"{db_applicant.opportunity_count}"
                                ),
                            )
                            session.add(evidence)

                            threshold_evidence = FlagEvidence(
                                flag_id=flag.id,
                                evidence_type="threshold",
                                key="mass_applicant_threshold",
                                value=str(mass_applicant_threshold),
                                description=f"Configured threshold: {mass_applicant_threshold}",
                            )
                            session.add(threshold_evidence)

                            # Update applicant flag count
                            db_applicant.flag_count = (db_applicant.flag_count or 0) + 1

                            mass_applicant_count += 1

                await session.commit()

        _sync_state.status = SyncStatus.COMPLETED
        _sync_state.message = (
            f"Sync complete: {new_count} new, {updated_count} updated, "
            f"{len(applicants_to_validate)} validated"
            + (f", {mass_applicant_count} mass applicant flags" if mass_applicant_count > 0 else "")
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
