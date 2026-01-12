"""SQLAlchemy database models for applicant validator.

This module defines a normalized relational schema for storing:
- Applicant data pulled from Lever
- LinkedIn profile data (cached)
- Validation runs and results
- Flags and risk indicators
- Audit logs for compliance

Design principles:
- UUIDs for primary keys (distributed-friendly)
- Soft deletes where appropriate
- Normalized child tables for structured data
- Proper indexes for query performance
- Audit timestamps on all tables
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from applicant_validator.database.base import Base

# =============================================================================
# Enums
# =============================================================================


class RiskLevel(str, Enum):
    """Risk level for applicants."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FlagSeverity(str, Enum):
    """Severity level for flags."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FlagCategory(str, Enum):
    """Categories for organizing flags."""

    IDENTITY = "identity"
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    RESUME = "resume"
    BEHAVIOR = "behavior"
    LOCATION = "location"
    OTHER = "other"


class ValidationStatus(str, Enum):
    """Status of a validation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditAction(str, Enum):
    """Types of auditable actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VALIDATE = "validate"
    ENRICH = "enrich"
    FLAG = "flag"
    REVIEW = "review"
    EXPORT = "export"


class UserRole(str, Enum):
    """User roles for access control."""

    SUPERADMIN = "superadmin"  # Full access + manage admins + system settings
    ADMIN = "admin"  # Full access + manage users (not superadmins)
    USER = "user"  # View + edit applicants, run validations
    VIEWER = "viewer"  # Read-only access


# =============================================================================
# Mixins
# =============================================================================


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# =============================================================================
# Core Models
# =============================================================================


class Applicant(Base, TimestampMixin, SoftDeleteMixin):
    """Applicant record pulled from Lever.

    This is the central entity that other tables reference.
    Stores both original Lever data and enriched data.
    """

    __tablename__ = "applicants"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Lever identifiers
    lever_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    lever_opportunity_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Basic info from Lever
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    email: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LinkedIn
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("linkedin_profiles.id"),
        nullable=True,
    )

    # Resume
    resume_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lever metadata
    lever_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lever_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    lever_owner_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lever_owner_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Validation summary (denormalized for quick queries)
    risk_level: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    validation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    flag_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Review status
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Manually added applicant (from Lever "Added manually" source)
    # These applicants may have missing email/phone which is expected
    is_manually_added: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Mass applicant detection fields
    # Track counts of jobs applied to and contact info provided
    opportunity_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    email_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    phone_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    linkedin_profile: Mapped["LinkedInProfile | None"] = relationship(
        back_populates="applicant",
        lazy="selectin",
    )
    sources: Mapped[list["ApplicantSource"]] = relationship(
        back_populates="applicant",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    validation_runs: Mapped[list["ValidationRun"]] = relationship(
        back_populates="applicant",
        lazy="selectin",
        order_by="desc(ValidationRun.created_at)",
    )
    flags: Mapped[list["Flag"]] = relationship(
        back_populates="applicant",
        lazy="selectin",
    )
    postings: Mapped[list["ApplicantPosting"]] = relationship(
        back_populates="applicant",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_applicants_email_lower", func.lower(email)),
        Index("ix_applicants_risk_validated", risk_level, last_validated_at),
    )


class ApplicantSource(Base, TimestampMixin):
    """Source of an applicant from Lever (e.g., job board, referral)."""

    __tablename__ = "applicant_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    applicant: Mapped["Applicant"] = relationship(back_populates="sources")

    __table_args__ = (UniqueConstraint("applicant_id", "source", name="uq_applicant_source"),)


class LinkedInProfile(Base, TimestampMixin):
    """Cached LinkedIn profile data.

    Stores enriched data from LinkedIn to avoid repeated API calls.
    Data may be from full API access or fallback scraping.
    """

    __tablename__ = "linkedin_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # LinkedIn identifiers
    linkedin_url: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
    )
    linkedin_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Profile data
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Validation status
    profile_exists: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Data source tracking
    data_source: Mapped[str] = mapped_column(
        String(50),
        default="fallback",
        nullable=False,
    )  # api, fallback, manual
    last_fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    applicant: Mapped["Applicant | None"] = relationship(
        back_populates="linkedin_profile",
    )
    experiences: Mapped[list["LinkedInExperience"]] = relationship(
        back_populates="profile",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="desc(LinkedInExperience.start_date)",
    )
    education: Mapped[list["LinkedInEducation"]] = relationship(
        back_populates="profile",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="desc(LinkedInEducation.start_date)",
    )
    skills: Mapped[list["LinkedInSkill"]] = relationship(
        back_populates="profile",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    certifications: Mapped[list["LinkedInCertification"]] = relationship(
        back_populates="profile",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="desc(LinkedInCertification.issue_date)",
    )


class LinkedInExperience(Base, TimestampMixin):
    """Work experience entry from a LinkedIn profile."""

    __tablename__ = "linkedin_experiences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("linkedin_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(500), nullable=False)
    company_linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Duration
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Employment type
    employment_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # full-time, part-time, contract, etc.

    # Relationships
    profile: Mapped["LinkedInProfile"] = relationship(back_populates="experiences")

    __table_args__ = (Index("ix_linkedin_exp_company", company),)


class LinkedInEducation(Base, TimestampMixin):
    """Education entry from a LinkedIn profile."""

    __tablename__ = "linkedin_education"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("linkedin_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # School details
    school: Mapped[str] = mapped_column(String(500), nullable=False)
    school_linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Duration
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile: Mapped["LinkedInProfile"] = relationship(back_populates="education")

    __table_args__ = (Index("ix_linkedin_edu_school", school),)


class LinkedInSkill(Base, TimestampMixin):
    """Skill entry from a LinkedIn profile."""

    __tablename__ = "linkedin_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("linkedin_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Skill details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    endorsement_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    profile: Mapped["LinkedInProfile"] = relationship(back_populates="skills")

    __table_args__ = (
        UniqueConstraint("profile_id", "name", name="uq_profile_skill"),
        Index("ix_linkedin_skill_name", name),
    )


class LinkedInCertification(Base, TimestampMixin):
    """Certification entry from a LinkedIn profile."""

    __tablename__ = "linkedin_certifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("linkedin_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Certification details
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issue_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    profile: Mapped["LinkedInProfile"] = relationship(back_populates="certifications")

    __table_args__ = (Index("ix_linkedin_cert_org", issuing_organization),)


class FlagType(Base, TimestampMixin):
    """Lookup table for flag types.

    Allows adding new flag types without schema changes.
    """

    __tablename__ = "flag_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Flag type definition
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        default=FlagCategory.OTHER.value,
        nullable=False,
        index=True,
    )
    default_severity: Mapped[str] = mapped_column(
        String(50),
        default=FlagSeverity.MEDIUM.value,
        nullable=False,
    )

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_flag: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )  # Whether to automatically apply this flag

    # Scoring weight (for risk calculation)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    flags: Mapped[list["Flag"]] = relationship(back_populates="flag_type")


class Flag(Base, TimestampMixin):
    """Individual flag raised for an applicant.

    Tracks specific issues detected during validation.
    """

    __tablename__ = "flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # References
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applicants.id"),
        nullable=False,
        index=True,
    )
    flag_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flag_types.id"),
        nullable=False,
        index=True,
    )
    validation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id"),
        nullable=True,
        index=True,
    )

    # Flag details
    severity: Mapped[str] = mapped_column(
        String(50),
        default=FlagSeverity.MEDIUM.value,
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resolution
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    applicant: Mapped["Applicant"] = relationship(back_populates="flags")
    flag_type: Mapped["FlagType"] = relationship(back_populates="flags")
    validation_run: Mapped["ValidationRun | None"] = relationship(back_populates="flags")
    evidence: Mapped[list["FlagEvidence"]] = relationship(
        back_populates="flag",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Prevent duplicate active flags of same type for same applicant
        UniqueConstraint(
            "applicant_id",
            "flag_type_id",
            "is_active",
            name="uq_active_flag_per_applicant",
        ),
        Index("ix_flags_active_severity", is_active, severity),
    )


class FlagEvidence(Base, TimestampMixin):
    """Evidence supporting a flag."""

    __tablename__ = "flag_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Evidence details
    evidence_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "matched_domain", "carrier_name", "ip_address"
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    flag: Mapped["Flag"] = relationship(back_populates="evidence")


class ValidationRun(Base, TimestampMixin):
    """A validation run for an applicant.

    Tracks each time we validate an applicant, including
    which rules were run and overall results.
    """

    __tablename__ = "validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Reference
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applicants.id"),
        nullable=False,
        index=True,
    )

    # Run metadata
    status: Mapped[str] = mapped_column(
        String(50),
        default=ValidationStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # user, api, scheduled, webhook
    trigger_source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # e.g., "lever_webhook", "manual_review"

    # Results summary
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rules_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rules_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flags_raised: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    applicant: Mapped["Applicant"] = relationship(back_populates="validation_runs")
    results: Mapped[list["ValidationResult"]] = relationship(
        back_populates="validation_run",
        lazy="selectin",
    )
    flags: Mapped[list["Flag"]] = relationship(back_populates="validation_run")
    config: Mapped[list["ValidationRunConfig"]] = relationship(
        back_populates="validation_run",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ValidationRunConfig(Base):
    """Configuration settings used for a validation run."""

    __tablename__ = "validation_run_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Configuration key-value pair
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_key: Mapped[str] = mapped_column(String(255), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    validation_run: Mapped["ValidationRun"] = relationship(back_populates="config")

    __table_args__ = (
        UniqueConstraint("validation_run_id", "rule_name", "config_key", name="uq_run_config"),
    )


class ValidationResult(Base, TimestampMixin):
    """Individual validation rule result.

    Stores the result of each rule in a validation run.
    """

    __tablename__ = "validation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Reference
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id"),
        nullable=False,
        index=True,
    )

    # Rule identification
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rule_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Result
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Skipped/error
    was_skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    validation_run: Mapped["ValidationRun"] = relationship(back_populates="results")
    evidence: Mapped[list["ValidationResultEvidence"]] = relationship(
        back_populates="result",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_validation_results_run_passed", validation_run_id, passed),)


class ValidationResultEvidence(Base):
    """Evidence data for a validation result."""

    __tablename__ = "validation_result_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Evidence details
    evidence_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "input_value", "matched_pattern", "api_response"
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    result: Mapped["ValidationResult"] = relationship(back_populates="evidence")


class AuditLog(Base):
    """Audit log for compliance and debugging.

    Tracks all significant actions in the system.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Action
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Actor
    actor_type: Mapped[str] = mapped_column(
        String(50),
        default="system",
        nullable=False,
    )  # system, user, api, webhook
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Context
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    changes: Mapped[list["AuditLogChange"]] = relationship(
        back_populates="audit_log",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_audit_logs_entity", entity_type, entity_id),
        Index("ix_audit_logs_actor", actor_type, actor_id),
    )


class AuditLogChange(Base):
    """Individual field change in an audit log entry."""

    __tablename__ = "audit_log_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    audit_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Change details
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    audit_log: Mapped["AuditLog"] = relationship(back_populates="changes")


# =============================================================================
# Validation Data Tables
# =============================================================================


class DataSourceType(str, Enum):
    """Source of validation data."""

    EXTERNAL_LIST = "external_list"  # From GitHub or other external source
    CUSTOM = "custom"  # Manually added by user
    API = "api"  # From API lookup


class DisposableEmailDomain(Base, TimestampMixin):
    """Known disposable email domains.

    This table stores domains from disposable email providers.
    Can be populated from external lists or manually added.
    """

    __tablename__ = "disposable_email_domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Domain
    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        default=DataSourceType.EXTERNAL_LIST.value,
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_disposable_domains_active", domain, is_active),)


class VoIPCarrier(Base, TimestampMixin):
    """Known VoIP carrier names/patterns.

    Stores carrier names that indicate VoIP service.
    Used for pattern matching against carrier lookup results.
    """

    __tablename__ = "voip_carriers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Carrier name or pattern
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Whether this is an exact match or substring match
    match_type: Mapped[str] = mapped_column(
        String(50),
        default="substring",
        nullable=False,
    )  # exact, substring, regex

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        default=DataSourceType.CUSTOM.value,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Confidence level (how confident we are this is VoIP)
    confidence: Mapped[str] = mapped_column(
        String(50),
        default="high",
        nullable=False,
    )  # high, medium, low

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class VoIPAreaCode(Base, TimestampMixin):
    """Known VoIP area codes.

    Stores area codes commonly used by VoIP services.
    """

    __tablename__ = "voip_area_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Area code (3 digits for US)
    area_code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
    )

    # Country code
    country_code: Mapped[str] = mapped_column(
        String(5),
        default="1",
        nullable=False,
    )  # 1 for US/Canada

    # Description
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        default=DataSourceType.CUSTOM.value,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ValidationDataSync(Base, TimestampMixin):
    """Tracks synchronization of validation data from external sources."""

    __tablename__ = "validation_data_syncs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # What was synced
    data_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # disposable_domains, voip_carriers, etc.

    # Source info
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Sync results
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )  # pending, running, completed, failed
    records_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


# =============================================================================
# Integration Settings Models
# =============================================================================


class IntegrationProvider(str, Enum):
    """Supported integration providers."""

    IPQUALITYSCORE = "ipqualityscore"
    TWILIO = "twilio"
    LEVER = "lever"
    LINKEDIN = "linkedin"


class IntegrationSetting(Base, TimestampMixin):
    """Stores API integration settings and credentials.

    Note: API keys are stored in the database for convenience.
    In production, consider using a secrets manager or encryption.
    """

    __tablename__ = "integration_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Provider identification
    provider: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Display name for UI
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Is this integration enabled?
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # API credentials (stored as key-value pairs in JSON-like structure)
    # For simple cases, we use separate columns
    # Using Text to support long JWT tokens (e.g., Lever API keys)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Additional configuration (JSON string for flexibility)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Validation settings
    fraud_score_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status tracking
    last_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_test_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Usage tracking
    monthly_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<IntegrationSetting {self.provider} enabled={self.is_enabled}>"

    @property
    def has_credentials(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.api_key or self.api_secret or self.account_id)

    @property
    def masked_api_key(self) -> str | None:
        """Return masked API key for display."""
        if not self.api_key:
            return None
        if len(self.api_key) <= 8:
            return "****"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    @property
    def masked_api_secret(self) -> str | None:
        """Return masked API secret for display."""
        if not self.api_secret:
            return None
        if len(self.api_secret) <= 8:
            return "****"
        return f"{self.api_secret[:4]}...{self.api_secret[-4:]}"


# =============================================================================
# Lever Posting Models
# =============================================================================


class LeverPosting(Base, TimestampMixin):
    """Lever job posting/opportunity details.

    Stores job posting information from Lever to display
    which jobs applicants have applied to.
    """

    __tablename__ = "lever_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Lever identifiers
    lever_posting_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Job details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Full-time, Part-time, etc.
    commitment: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status: published, internal, closed
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Lever metadata
    lever_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    applicant_postings: Mapped[list["ApplicantPosting"]] = relationship(
        back_populates="posting",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<LeverPosting {self.title} ({self.lever_posting_id})>"


class ApplicantPosting(Base, TimestampMixin):
    """Junction table linking applicants to job postings they applied to.

    This enables tracking which jobs each applicant has applied to,
    which is useful for mass applicant detection and review.
    """

    __tablename__ = "applicant_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lever_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Lever opportunity ID for this specific application
    lever_opportunity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Application details
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stage: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    applicant: Mapped["Applicant"] = relationship(back_populates="postings")
    posting: Mapped["LeverPosting"] = relationship(back_populates="applicant_postings")

    __table_args__ = (
        UniqueConstraint("applicant_id", "posting_id", name="uq_applicant_posting"),
        UniqueConstraint("lever_opportunity_id", name="uq_lever_opportunity_id"),
    )


# =============================================================================
# System Configuration
# =============================================================================


class SystemConfig(Base, TimestampMixin):
    """System configuration key-value store.

    Stores configurable settings like validation thresholds that can be
    adjusted through the admin panel without code changes.
    """

    __tablename__ = "system_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Configuration key (e.g., "mass_applicant_threshold")
    key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Configuration value (stored as string, parsed by consumers)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Human-readable description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Value type hint for UI (integer, string, boolean, json)
    value_type: Mapped[str] = mapped_column(
        String(50),
        default="string",
        nullable=False,
    )

    # Category for grouping in UI
    category: Mapped[str] = mapped_column(
        String(100),
        default="general",
        nullable=False,
        index=True,
    )

    # Whether this setting is editable via UI
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        """String representation."""
        return f"<SystemConfig {self.key}={self.value}>"


# =============================================================================
# Authentication Models
# =============================================================================


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account for authentication.

    Users are created by admins only (no self-registration).
    Superadmin is seeded during initial setup.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Role and permissions
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.USER.value,
        nullable=False,
        index=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    must_change_email: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Audit: who created this user
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    created_by: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[created_by_id],
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<User {self.email} role={self.role}>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in (UserRole.ADMIN.value, UserRole.SUPERADMIN.value)

    @property
    def is_superadmin(self) -> bool:
        """Check if user is superadmin."""
        return self.role == UserRole.SUPERADMIN.value


class UserSession(Base, TimestampMixin):
    """User session for JWT token tracking.

    Allows session revocation and tracking.
    """

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # JWT identifier for this session
    jti: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Revocation status
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Client info for security auditing
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserSession {self.jti[:8]}... user={self.user_id}>"

    @property
    def is_valid(self) -> bool:
        """Check if session is still valid."""
        from datetime import UTC

        return not self.is_revoked and self.expires_at > datetime.now(UTC)
