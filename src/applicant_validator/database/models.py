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
