"""Data models for the applicant validator."""

from applicant_validator.models.applicant import Applicant
from applicant_validator.models.linkedin import Education, Experience, LinkedInProfile
from applicant_validator.models.validation import (
    RiskLevel,
    Severity,
    ValidationReport,
    ValidationResult,
)

__all__ = [
    "Applicant",
    "Education",
    "Experience",
    "LinkedInProfile",
    "RiskLevel",
    "Severity",
    "ValidationReport",
    "ValidationResult",
]
