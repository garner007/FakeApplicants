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
    PaginatedApplicantsResponse,
)
from applicant_validator.database import Applicant, Flag, get_session

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
        is_reviewed=applicant.is_reviewed,
        reviewed_at=applicant.reviewed_at,
        created_at=applicant.created_at,
        flags=[_flag_to_response(f) for f in applicant.flags if f.is_active],
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
        is_reviewed=applicant.is_reviewed,
        reviewed_at=applicant.reviewed_at,
        reviewed_by=applicant.reviewed_by,
        created_at=applicant.created_at,
        updated_at=applicant.updated_at,
        flags=[_flag_to_response(f) for f in applicant.flags if f.is_active],
    )


@router.get("", response_model=PaginatedApplicantsResponse)
async def list_applicants(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Literal["created_at", "updated_at", "name", "risk_level", "flag_count"] = Query(
        "created_at", description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    is_reviewed: bool | None = Query(None, description="Filter by review status"),
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


@router.get("/{applicant_id}", response_model=ApplicantResponse)
async def get_applicant(applicant_id: UUID) -> ApplicantResponse:
    """Get a single applicant by ID."""
    async with get_session() as session:
        query = (
            select(Applicant)
            .where(Applicant.id == applicant_id)
            .where(Applicant.is_deleted == False)  # noqa: E712
            .options(selectinload(Applicant.flags).selectinload(Flag.flag_type))
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
            .options(selectinload(Applicant.flags).selectinload(Flag.flag_type))
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
