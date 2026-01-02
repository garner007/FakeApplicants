"""Validation result and report models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class OrderedEnum(str, Enum):
    """Base class for enums that support ordering."""

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        members = list(type(self))
        return members.index(self) < members.index(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        members = list(type(self))
        return members.index(self) > members.index(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self == other or self > other


class Severity(OrderedEnum):
    """Severity level for validation rule failures.

    Ordered from lowest to highest severity.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(OrderedEnum):
    """Overall risk level for an applicant.

    Ordered from lowest to highest risk.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationResult(BaseModel):
    """Result from a single validation rule execution."""

    rule_name: str = Field(..., description="Unique identifier for the validation rule")
    passed: bool = Field(..., description="Whether the validation passed")
    severity: Severity = Field(..., description="Severity level of this rule")
    message: str = Field(..., description="Human-readable result message")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details about the validation result",
    )


class ValidationReport(BaseModel):
    """Complete validation report for an applicant."""

    applicant_id: str = Field(..., description="ID of the validated applicant")
    applicant_name: str = Field(..., description="Name of the validated applicant")
    timestamp: datetime = Field(..., description="When the validation was performed")
    results: list[ValidationResult] = Field(..., description="Individual validation results")
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall trustworthiness score (0-100, higher is better)",
    )
    risk_level: RiskLevel = Field(..., description="Overall risk assessment")
    flags: list[str] = Field(default_factory=list, description="Warning flags for manual review")

    @field_validator("overall_score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is within valid range."""
        if v < 0.0 or v > 100.0:
            msg = "overall_score must be between 0 and 100"
            raise ValueError(msg)
        return v

    @property
    def passed(self) -> bool:
        """Whether the applicant passed validation (not HIGH risk)."""
        return self.risk_level != RiskLevel.HIGH

    @property
    def failed_count(self) -> int:
        """Number of validation rules that failed."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def passed_count(self) -> int:
        """Number of validation rules that passed."""
        return sum(1 for r in self.results if r.passed)

    @property
    def total_count(self) -> int:
        """Total number of validation rules executed."""
        return len(self.results)
