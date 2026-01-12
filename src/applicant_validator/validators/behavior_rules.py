"""Behavior-based validation rules."""

import logging
from typing import Any, ClassVar

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)

logger = logging.getLogger(__name__)


class MassApplicantRule(ValidationRule):
    """Validates that an applicant hasn't applied to too many positions.

    This rule flags applicants who have applied to multiple job postings,
    which is a common indicator of fraudulent mass-application behavior.
    The threshold is configurable via the admin panel.
    """

    name = "mass_applicant"
    description = "Check if applicant has applied to multiple positions"
    category = "behavior"
    default_severity = RuleSeverity.MEDIUM
    version = "1.0.0"
    checks_fields: ClassVar[list[str]] = ["opportunity_count"]
    trigger_examples: ClassVar[list[str]] = [
        "Applicant applied to 5+ positions",
        "Multiple applications within a short time period",
        "Applying to unrelated roles simultaneously",
    ]
    rationale = (
        "Fraudulent applicants often apply to multiple positions at once, "
        "hoping to increase their chances of getting through. Legitimate applicants "
        "typically apply to one or a few relevant positions. A high number of "
        "applications may indicate automated or fraudulent behavior."
    )

    # Default threshold - can be overridden by database config
    DEFAULT_THRESHOLD = 5

    def __init__(self) -> None:
        """Initialize the rule."""
        self._threshold: int | None = None
        self._threshold_checked: bool = False

    async def _get_threshold(self) -> int:
        """Get the mass applicant threshold from config or use default.

        Returns:
            The configured threshold for flagging mass applicants.
        """
        if self._threshold is not None:
            return self._threshold

        # Try to get threshold from database config
        try:
            from applicant_validator.database.base import get_session
            from applicant_validator.services.system_config import (
                get_system_config_service,
            )

            async with get_session() as session:
                service = get_system_config_service(session)
                config_value = await service.get("mass_applicant_threshold")

                if config_value is not None:
                    self._threshold = int(config_value)
                    logger.info(f"Mass applicant threshold from config: {self._threshold}")
                    return self._threshold

        except Exception as e:
            logger.debug(f"Could not get threshold from database config: {e}")

        # Fall back to default
        self._threshold = self.DEFAULT_THRESHOLD
        return self._threshold

    async def validate(self, data: dict[str, Any]) -> RuleResult:
        """Validate that the applicant hasn't applied to too many positions.

        Args:
            data: Dictionary containing applicant data including 'opportunity_count'.

        Returns:
            RuleResult with pass/fail status and evidence.
        """
        opportunity_count = data.get("opportunity_count", 1)

        # Skip if we don't have opportunity count data
        if opportunity_count is None or opportunity_count < 1:
            return RuleResult.create_skip(self.name, "No opportunity count data available")

        threshold = await self._get_threshold()

        evidence = [
            ValidationEvidence(
                evidence_type="opportunity_count",
                key="count",
                value=str(opportunity_count),
                description=f"Applicant has applied to {opportunity_count} position(s)",
            ),
            ValidationEvidence(
                evidence_type="threshold",
                key="threshold",
                value=str(threshold),
                description=f"Current threshold is {threshold} applications",
            ),
        ]

        if opportunity_count >= threshold:
            return RuleResult.create_fail(
                rule_name=self.name,
                message=(
                    f"Applicant applied to {opportunity_count} positions "
                    f"(threshold: {threshold})"
                ),
                severity=self.default_severity,
                evidence=evidence,
            )

        return RuleResult.create_pass(
            self.name,
            f"Applicant has {opportunity_count} application(s) (under threshold of {threshold})",
        )
