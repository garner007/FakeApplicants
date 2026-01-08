"""Base classes for validation rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleSeverity(str, Enum):
    """Severity levels for validation rule failures."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationEvidence:
    """Evidence collected during validation."""

    evidence_type: str
    key: str
    value: str
    description: str | None = None


@dataclass
class RuleResult:
    """Result of a validation rule execution."""

    rule_name: str
    passed: bool
    message: str | None = None
    severity: RuleSeverity | None = None
    score: float | None = None
    evidence: list[ValidationEvidence] = field(default_factory=list)
    duration_ms: int | None = None
    was_skipped: bool = False
    skip_reason: str | None = None

    @classmethod
    def create_skip(cls, rule_name: str, reason: str) -> "RuleResult":
        """Create a skipped result."""
        return cls(
            rule_name=rule_name,
            passed=True,  # Skipped rules don't fail
            was_skipped=True,
            skip_reason=reason,
        )

    @classmethod
    def create_pass(cls, rule_name: str, message: str | None = None) -> "RuleResult":
        """Create a passing result."""
        return cls(rule_name=rule_name, passed=True, message=message)

    @classmethod
    def create_fail(
        cls,
        rule_name: str,
        message: str,
        severity: RuleSeverity = RuleSeverity.MEDIUM,
        evidence: list[ValidationEvidence] | None = None,
    ) -> "RuleResult":
        """Create a failing result."""
        return cls(
            rule_name=rule_name,
            passed=False,
            message=message,
            severity=severity,
            evidence=evidence or [],
        )

    # Keep backward compatible aliases
    skip = create_skip
    fail = create_fail


class ValidationRule(ABC):
    """Abstract base class for validation rules."""

    # Class-level attributes that subclasses should override
    name: str = "base_rule"
    description: str = "Base validation rule"
    category: str = "other"
    default_severity: RuleSeverity = RuleSeverity.MEDIUM
    version: str = "1.0.0"
    # Additional metadata for documentation
    checks_fields: list[str] = []  # Which applicant fields this rule examines
    trigger_examples: list[str] = []  # Examples of what triggers this rule
    rationale: str = ""  # Why this check matters

    @abstractmethod
    async def validate(self, data: dict[str, Any]) -> RuleResult:
        """Execute the validation rule.

        Args:
            data: Dictionary containing applicant data to validate.
                  Expected keys depend on the specific rule.

        Returns:
            RuleResult indicating whether validation passed or failed.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
