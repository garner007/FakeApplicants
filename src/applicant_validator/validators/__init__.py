"""Validation rules for applicant data."""

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)
from applicant_validator.validators.email_rules import DisposableEmailRule
from applicant_validator.validators.phone_rules import VoIPPhoneRule

__all__ = [
    "DisposableEmailRule",
    "RuleResult",
    "RuleSeverity",
    "ValidationEvidence",
    "ValidationRule",
    "VoIPPhoneRule",
]
