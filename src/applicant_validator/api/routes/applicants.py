"""Applicant API routes."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

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
from applicant_validator.database import (
    Applicant,
    ApplicantPosting,
    ApplicantSource,
    Flag,
    FlagType,
    get_session,
)
from applicant_validator.services.validation import (
    ensure_flag_types,
    validate_applicant,
)

router = APIRouter(prefix="/applicants", tags=["applicants"])


def _flag_to_response(flag: Flag) -> FlagResponse:
    """Convert a Flag model to FlagResponse."""
    return FlagResponse(
        id=flag.id,
        flag_type_code=flag.flag_type.code,
        flag_type_name=flag.flag_type.name,
        category=flag.flag_type.category,
        severity=flag.severity,
        message=flag.message,
        is_active=flag.is_active,
        created_at=flag.created_at,
    )


def _posting_to_response(applicant_posting: ApplicantPosting) -> PostingResponse:
    """Convert an ApplicantPosting model to PostingResponse."""
    posting = applicant_posting.posting
    return PostingResponse(
        id=posting.id,
        lever_posting_id=posting.lever_posting_id,
        title=posting.title,
        team=posting.team,
        department=posting.department,
        location=posting.location,
        commitment=posting.commitment,
        state=posting.state,
    )


def _applicant_to_list_response(applicant: Applicant) -> ApplicantListResponse:
    """Convert an Applicant model to ApplicantListResponse."""
    return ApplicantListResponse(
        id=applicant.id,
        lever_id=applicant.lever_id,
        name=applicant.name,
        email=applicant.email,
        phone=applicant.phone,
        location=applicant.location,
        risk_level=applicant.risk_level,
        flag_count=applicant.flag_count,
        opportunity_count=applicant.opportunity_count,
        is_reviewed=applicant.is_reviewed,
        reviewed_at=applicant.reviewed_at,
        created_at=applicant.created_at,
        lever_created_at=applicant.lever_created_at,
        flags=[_flag_to_response(f) for f in applicant.flags if f.is_active],
        sources=[s.source for s in applicant.sources],
        assigned_ta=applicant.lever_owner_name,
    )


def _applicant_to_response(applicant: Applicant) -> ApplicantResponse:
    """Convert an Applicant model to ApplicantResponse."""
    return ApplicantResponse(
        id=applicant.id,
        lever_id=applicant.lever_id,
        name=applicant.name,
        email=applicant.email,
        phone=applicant.phone,
        location=applicant.location,
        linkedin_url=applicant.linkedin_url,
        risk_level=applicant.risk_level,
        validation_score=applicant.validation_score,
        flag_count=applicant.flag_count,
        opportunity_count=applicant.opportunity_count,
        is_reviewed=applicant.is_reviewed,
        reviewed_at=applicant.reviewed_at,
        reviewed_by=applicant.reviewed_by,
        created_at=applicant.created_at,
        updated_at=applicant.updated_at,
        lever_created_at=applicant.lever_created_at,
        flags=[_flag_to_response(f) for f in applicant.flags if f.is_active],
        sources=[s.source for s in applicant.sources],
        postings=[_posting_to_response(p) for p in applicant.postings],
        assigned_ta=applicant.lever_owner_name,
    )


@router.get("", response_model=PaginatedApplicantsResponse)
async def list_applicants(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Literal[
        "created_at", "updated_at", "name", "risk_level", "flag_count", "lever_created_at"
    ] = Query("created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    is_reviewed: bool | None = Query(None, description="Filter by review status"),
    assigned_ta: str | None = Query(None, description="Filter by assigned TA name"),
    source: str | None = Query(None, description="Filter by applicant source"),
    flag_type: str | None = Query(None, description="Filter by flag type code"),
) -> PaginatedApplicantsResponse:
    """List all applicants with pagination and sorting."""
    async with get_session() as session:
        # Base query
        query = select(Applicant).where(Applicant.is_deleted == False)  # noqa: E712

        # Apply filters
        if risk_level:
            query = query.where(Applicant.risk_level == risk_level)
        if is_reviewed is not None:
            query = query.where(Applicant.is_reviewed == is_reviewed)
        if assigned_ta:
            query = query.where(Applicant.lever_owner_name == assigned_ta)
        if source:
            # Join with ApplicantSource to filter by source
            query = query.where(
                Applicant.id.in_(
                    select(ApplicantSource.applicant_id).where(ApplicantSource.source == source)
                )
            )
        if flag_type:
            # Join with Flag and FlagType to filter by flag type code
            query = query.where(
                Applicant.id.in_(
                    select(Flag.applicant_id)
                    .join(FlagType, Flag.flag_type_id == FlagType.id)
                    .where(FlagType.code == flag_type)
                    .where(Flag.is_active == True)  # noqa: E712
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0

        # Apply sorting
        sort_column = getattr(Applicant, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load flags with their types
        query = query.options(selectinload(Applicant.flags).selectinload(Flag.flag_type))

        # Execute query
        result = await session.execute(query)
        applicants = result.scalars().all()

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        return PaginatedApplicantsResponse(
            items=[_applicant_to_list_response(a) for a in applicants],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/tas", response_model=TAListResponse)
async def list_tas() -> TAListResponse:
    """Get list of unique assigned TAs for filtering."""
    async with get_session() as session:
        query = (
            select(Applicant.lever_owner_name)
            .where(Applicant.is_deleted == False)  # noqa: E712
            .where(Applicant.lever_owner_name.isnot(None))
            .distinct()
            .order_by(Applicant.lever_owner_name)
        )
        result = await session.execute(query)
        tas = [row[0] for row in result.fetchall()]
        return TAListResponse(tas=tas)


@router.get("/sources", response_model=SourceListResponse)
async def list_sources() -> SourceListResponse:
    """Get list of unique applicant sources for filtering."""
    async with get_session() as session:
        query = select(ApplicantSource.source).distinct().order_by(ApplicantSource.source)
        result = await session.execute(query)
        sources = [row[0] for row in result.fetchall()]
        return SourceListResponse(sources=sources)


@router.get("/flag-types", response_model=FlagTypeListResponse)
async def list_flag_types() -> FlagTypeListResponse:
    """Get list of flag types that have active flags in the database."""
    async with get_session() as session:
        # Only return flag types that have at least one active flag
        query = (
            select(FlagType)
            .where(
                FlagType.id.in_(
                    select(Flag.flag_type_id)
                    .join(Applicant, Flag.applicant_id == Applicant.id)
                    .where(Flag.is_active == True)  # noqa: E712
                    .where(Applicant.is_deleted == False)  # noqa: E712
                    .distinct()
                )
            )
            .order_by(FlagType.category, FlagType.name)
        )
        result = await session.execute(query)
        flag_types = result.scalars().all()
        return FlagTypeListResponse(
            flag_types=[
                FlagTypeResponse(code=ft.code, name=ft.name, category=ft.category)
                for ft in flag_types
            ]
        )


@router.get("/risk-levels", response_model=RiskLevelListResponse)
async def list_risk_levels() -> RiskLevelListResponse:
    """Get list of risk levels for filtering."""
    async with get_session() as session:
        query = (
            select(Applicant.risk_level)
            .where(Applicant.is_deleted == False)  # noqa: E712
            .where(Applicant.risk_level.isnot(None))
            .distinct()
            .order_by(Applicant.risk_level)
        )
        result = await session.execute(query)
        risk_levels = [row[0] for row in result.fetchall()]
        return RiskLevelListResponse(risk_levels=risk_levels)


@router.get("/{applicant_id}", response_model=ApplicantResponse)
async def get_applicant(applicant_id: UUID) -> ApplicantResponse:
    """Get a single applicant by ID."""
    async with get_session() as session:
        query = (
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .where(Applicant.is_deleted == False)  # noqa: E712
            .options(
                selectinload(Applicant.flags).selectinload(Flag.flag_type),
                selectinload(Applicant.postings).selectinload(ApplicantPosting.posting),
            )
        )
        result = await session.execute(query)
        applicant = result.scalar_one_or_none()

        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant not found")

        return _applicant_to_response(applicant)


@router.patch("/{applicant_id}", response_model=ApplicantResponse)
async def update_applicant(
    applicant_id: UUID,
    update: ApplicantUpdateRequest,
) -> ApplicantResponse:
    """Update applicant fields (e.g., mark as reviewed)."""
    async with get_session() as session:
        query = (
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .where(Applicant.is_deleted == False)  # noqa: E712
            .options(
                selectinload(Applicant.flags).selectinload(Flag.flag_type),
                selectinload(Applicant.postings).selectinload(ApplicantPosting.posting),
            )
        )
        result = await session.execute(query)
        applicant = result.scalar_one_or_none()

        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Update fields
        if update.is_reviewed is not None:
            applicant.is_reviewed = update.is_reviewed
            if update.is_reviewed:
                applicant.reviewed_at = datetime.now(UTC)
            else:
                applicant.reviewed_at = None
                applicant.reviewed_by = None

        if update.reviewed_by is not None:
            applicant.reviewed_by = update.reviewed_by

        await session.commit()
        await session.refresh(applicant)

        return _applicant_to_response(applicant)


@router.post("/{applicant_id}/validate", response_model=ValidateApplicantResponse)
async def validate_single_applicant(applicant_id: UUID) -> ValidateApplicantResponse:
    """Run validation rules against a single applicant.

    This endpoint allows on-demand validation of individual applicants,
    useful for saving API credits by selectively validating profiles.
    """
    async with get_session() as session:
        # Fetch the applicant with all related data
        query = (
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .where(Applicant.is_deleted == False)  # noqa: E712
            .options(
                selectinload(Applicant.flags).selectinload(Flag.flag_type),
                selectinload(Applicant.postings).selectinload(ApplicantPosting.posting),
                selectinload(Applicant.sources),
            )
        )
        result = await session.execute(query)
        applicant = result.scalar_one_or_none()

        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Store previous risk level for comparison
        previous_risk_level = applicant.risk_level

        # Deactivate existing flags before re-validation
        for flag in applicant.flags:
            if flag.is_active:
                flag.is_active = False

        # Reset flag count before validation
        applicant.flag_count = 0

        # Ensure flag types exist
        flag_types = await ensure_flag_types(session)

        # Run validation
        validation_run = await validate_applicant(
            session=session,
            applicant=applicant,
            flag_types=flag_types,
            triggered_by="manual",
        )

        await session.commit()

        # Refresh to get updated flags
        await session.refresh(applicant)

        # Reload flags with their types for the response
        query = (
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .options(
                selectinload(Applicant.flags).selectinload(Flag.flag_type),
                selectinload(Applicant.postings).selectinload(ApplicantPosting.posting),
                selectinload(Applicant.sources),
            )
        )
        result = await session.execute(query)
        applicant = result.scalar_one_or_none()

        # Should not be None since we validated applicant_id exists earlier
        assert applicant is not None, "Applicant should exist after validation"

        # Build response message
        if validation_run.flags_raised == 0:
            message = "Validation complete. No issues found."
        elif validation_run.flags_raised == 1:
            message = "Validation complete. 1 issue flagged."
        else:
            message = f"Validation complete. {validation_run.flags_raised} issues flagged."

        return ValidateApplicantResponse(
            applicant=_applicant_to_response(applicant),
            rules_passed=validation_run.rules_passed,
            rules_failed=validation_run.rules_failed,
            rules_skipped=validation_run.rules_skipped,
            flags_raised=validation_run.flags_raised,
            previous_risk_level=previous_risk_level,
            new_risk_level=applicant.risk_level,
            message=message,
        )
