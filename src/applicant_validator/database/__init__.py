"""Database module for applicant validator."""

from applicant_validator.database.base import Base, get_session, init_db
from applicant_validator.database.models import (
    Applicant,
    ApplicantSource,
    AuditAction,
    AuditLog,
    AuditLogChange,
    Flag,
    FlagCategory,
    FlagEvidence,
    FlagSeverity,
    FlagType,
    LinkedInCertification,
    LinkedInEducation,
    LinkedInExperience,
    LinkedInProfile,
    LinkedInSkill,
    RiskLevel,
    ValidationResult,
    ValidationResultEvidence,
    ValidationRun,
    ValidationRunConfig,
    ValidationStatus,
)

__all__ = [
    # Core models
    "Applicant",
    "ApplicantSource",
    # Enums
    "AuditAction",
    "AuditLog",
    "AuditLogChange",
    # Base and utilities
    "Base",
    "Flag",
    "FlagCategory",
    "FlagEvidence",
    "FlagSeverity",
    "FlagType",
    "LinkedInCertification",
    "LinkedInEducation",
    "LinkedInExperience",
    "LinkedInProfile",
    "LinkedInSkill",
    "RiskLevel",
    "ValidationResult",
    "ValidationResultEvidence",
    "ValidationRun",
    "ValidationRunConfig",
    "ValidationStatus",
    "get_session",
    "init_db",
]
