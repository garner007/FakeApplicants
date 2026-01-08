"""Applicant API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FlagResponse(BaseModel):
    """Flag information for an applicant."""

    id: UUID
    flag_type_code: str
    flag_type_name: str
    category: str
    severity: str
    message: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicantResponse(BaseModel):
    """Applicant response model."""

    id: UUID
    lever_id: str
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    resume_url: str | None = None
    risk_level: str | None = None
    validation_score: float | None = None
    flag_count: int = 0
    is_reviewed: bool = False
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    created_at: datetime
    updated_at: datetime
    lever_created_at: datetime | None = None
    flags: list[FlagResponse] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    assigned_ta: str | None = None

    model_config = {"from_attributes": True}


class ApplicantListResponse(BaseModel):
    """Simplified applicant for list view."""

    id: UUID
    lever_id: str
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    risk_level: str | None = None
    flag_count: int = 0
    is_reviewed: bool = False
    reviewed_at: datetime | None = None
    created_at: datetime
    lever_created_at: datetime | None = None
    flags: list[FlagResponse] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    assigned_ta: str | None = None

    model_config = {"from_attributes": True}


class PaginatedApplicantsResponse(BaseModel):
    """Paginated list of applicants."""

    items: list[ApplicantListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApplicantUpdateRequest(BaseModel):
    """Request to update applicant fields."""

    is_reviewed: bool | None = None
    reviewed_by: str | None = None


class TAListResponse(BaseModel):
    """Response with list of assigned TAs."""

    tas: list[str] = Field(default_factory=list)


class SourceListResponse(BaseModel):
    """Response with list of applicant sources."""

    sources: list[str] = Field(default_factory=list)
