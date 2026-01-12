"""Validation rules for applicant data."""

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)
from applicant_validator.validators.behavior_rules import MassApplicantRule
from applicant_validator.validators.email_rules import DisposableEmailRule
from applicant_validator.validators.linkedin_rules import InvalidLinkedInUrlRule
from applicant_validator.validators.location_rules import NonUSLocationRule
from applicant_validator.validators.phone_rules import NonUSPhoneRule, VoIPPhoneRule

__all__ = [
    "DisposableEmailRule",
    "InvalidLinkedInUrlRule",
    "MassApplicantRule",
    "NonUSLocationRule",
    "NonUSPhoneRule",
    "RuleResult",
    "RuleSeverity",
    "ValidationEvidence",
    "ValidationRule",
    "VoIPPhoneRule",
]
