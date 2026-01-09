"""Re-validation API routes for re-running validation rules on existing applicants."""

from datetime import UTC, datetime, timedelta
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from applicant_validator.database import (
    Applicant,
    Flag,
    get_session,
)
from applicant_validator.services.validation import ensure_flag_types, validate_applicant

router = APIRouter(prefix="/revalidate", tags=["revalidate"])


class RevalidateStatus(str, Enum):
    """Status of a re-validation operation."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RevalidateState:
    """Global re-validation state tracker."""

    status: RevalidateStatus = RevalidateStatus.IDLE
    progress: int = 0
    total: int = 0
    message: str = ""
    last_run_at: datetime | None = None
    error: str | None = None

    # Results tracking
    applicants_processed: int = 0
    flags_raised: int = 0
    flags_cleared: int = 0
    risk_level_changes: int = 0
    current_applicant_name: str | None = None


# Global re-validation state
_revalidate_state = RevalidateState()


class RevalidateRequest(BaseModel):
    """Request to start a re-validation operation."""

    days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Only re-validate applicants created within the last N days (null for all)",
    )
    clear_existing_flags: bool = Field(
        default=True,
        description="Clear existing flags before re-validating",
    )


class RevalidateStatusResponse(BaseModel):
    """Response with current re-validation status."""

    status: RevalidateStatus
    progress: int
    total: int
    message: str
    last_run_at: datetime | None
    error: str | None = None
    applicants_processed: int
    flags_raised: int
    flags_cleared: int
    risk_level_changes: int
    current_applicant_name: str | None = None


class RevalidateResponse(BaseModel):
    """Response after starting a re-validation."""

    message: str
    status: RevalidateStatus


async def _perform_revalidation(
    days: int | None = None,
    clear_existing_flags: bool = True,
) -> None:
    """Perform the actual re-validation operation."""
    try:
        _revalidate_state.status = RevalidateStatus.RUNNING
        _revalidate_state.progress = 0
        _revalidate_state.total = 0
        _revalidate_state.message = "Fetching applicants to re-validate..."
        _revalidate_state.error = None
        _revalidate_state.applicants_processed = 0
        _revalidate_state.flags_raised = 0
        _revalidate_state.flags_cleared = 0
        _revalidate_state.risk_level_changes = 0
        _revalidate_state.current_applicant_name = None

        # Fetch applicants based on filters
        async with get_session() as session:
            query = select(Applicant).where(Applicant.is_deleted == False)  # noqa: E712

            # Apply age filter based on application date (lever_created_at)
            if days:
                cutoff_date = datetime.now(UTC) - timedelta(days=days)
                query = query.where(Applicant.lever_created_at >= cutoff_date)

            result = await session.execute(query)
            applicants = result.scalars().all()
            applicant_ids = [a.id for a in applicants]

        if not applicant_ids:
            _revalidate_state.status = RevalidateStatus.COMPLETED
            _revalidate_state.message = "No applicants found matching the filters"
            _revalidate_state.last_run_at = datetime.now(UTC)
            return

        _revalidate_state.total = len(applicant_ids)
        _revalidate_state.message = f"Re-validating {len(applicant_ids)} applicants..."

        # Process each applicant
        async with get_session() as session:
            # Ensure flag types exist first
            flag_types = await ensure_flag_types(session)
            await session.commit()

            for i, applicant_id in enumerate(applicant_ids, 1):
                # Fetch the applicant in this session
                result = await session.execute(
                    select(Applicant).where(Applicant.id == applicant_id)
                )
                applicant = result.scalar_one_or_none()

                if not applicant:
                    continue

                _revalidate_state.current_applicant_name = applicant.name
                old_risk_level = applicant.risk_level

                # Clear existing flags if requested
                if clear_existing_flags:
                    # Count existing active flags
                    flag_count_result = await session.execute(
                        select(Flag)
                        .where(Flag.applicant_id == applicant.id)
                        .where(Flag.is_active == True)  # noqa: E712
                    )
                    existing_flags = flag_count_result.scalars().all()
                    _revalidate_state.flags_cleared += len(existing_flags)

                    # Delete all flags for this applicant
                    await session.execute(delete(Flag).where(Flag.applicant_id == applicant.id))
                    await session.flush()

                # Re-run validation
                validation_run = await validate_applicant(
                    session, applicant, flag_types, "revalidation"
                )

                # Track statistics
                _revalidate_state.flags_raised += validation_run.flags_raised
                if applicant.risk_level != old_risk_level:
                    _revalidate_state.risk_level_changes += 1

                _revalidate_state.applicants_processed += 1
                _revalidate_state.progress = i

                if i % 50 == 0:
                    _revalidate_state.message = (
                        f"Re-validated {i}/{len(applicant_ids)} applicants..."
                    )
                    await session.commit()

            await session.commit()

        _revalidate_state.status = RevalidateStatus.COMPLETED
        processed = _revalidate_state.applicants_processed
        raised = _revalidate_state.flags_raised
        cleared = _revalidate_state.flags_cleared
        risk_changes = _revalidate_state.risk_level_changes
        _revalidate_state.message = (
            f"Re-validation complete: {processed} applicants processed, "
            f"{raised} flags raised, {cleared} flags cleared, "
            f"{risk_changes} risk level changes"
        )
        _revalidate_state.last_run_at = datetime.now(UTC)
        _revalidate_state.current_applicant_name = None

    except Exception as e:
        _revalidate_state.status = RevalidateStatus.FAILED
        _revalidate_state.error = str(e)
        _revalidate_state.message = f"Re-validation failed: {e!s}"
        _revalidate_state.current_applicant_name = None


@router.get("/status", response_model=RevalidateStatusResponse)
async def get_revalidate_status() -> RevalidateStatusResponse:
    """Get the current re-validation status."""
    return RevalidateStatusResponse(
        status=_revalidate_state.status,
        progress=_revalidate_state.progress,
        total=_revalidate_state.total,
        message=_revalidate_state.message,
        last_run_at=_revalidate_state.last_run_at,
        error=_revalidate_state.error,
        applicants_processed=_revalidate_state.applicants_processed,
        flags_raised=_revalidate_state.flags_raised,
        flags_cleared=_revalidate_state.flags_cleared,
        risk_level_changes=_revalidate_state.risk_level_changes,
        current_applicant_name=_revalidate_state.current_applicant_name,
    )


@router.post("/start", response_model=RevalidateResponse)
async def start_revalidation(
    request: RevalidateRequest,
    background_tasks: BackgroundTasks,
) -> RevalidateResponse:
    """Start a re-validation operation on existing applicants."""
    if _revalidate_state.status == RevalidateStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Re-validation already in progress")

    # Reset state and start re-validation in background
    _revalidate_state.status = RevalidateStatus.RUNNING
    _revalidate_state.progress = 0
    _revalidate_state.total = 0
    _revalidate_state.message = "Starting re-validation..."
    _revalidate_state.error = None
    _revalidate_state.applicants_processed = 0
    _revalidate_state.flags_raised = 0
    _revalidate_state.flags_cleared = 0
    _revalidate_state.risk_level_changes = 0

    background_tasks.add_task(
        _perform_revalidation,
        request.days,
        request.clear_existing_flags,
    )

    filter_str = (
        f" for applicants who applied in the last {request.days} days"
        if request.days
        else " for all applicants"
    )

    return RevalidateResponse(
        message=f"Re-validation started{filter_str}",
        status=RevalidateStatus.RUNNING,
    )
