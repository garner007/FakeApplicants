"""LinkedIn validation rules."""

import re
from typing import Any, ClassVar
from urllib.parse import urlparse

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)


def is_linkedin_profile_url(url: str | None) -> bool:
    """Check if a LinkedIn URL is a valid profile URL.

    Args:
        url: LinkedIn URL to check.

    Returns:
        True if it's a profile URL (/in/... or /pub/...), False otherwise.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return bool(re.match(r"^/(in|pub)/[^/?]+", path))
    except Exception:
        return False


def get_linkedin_url_type(url: str | None) -> str | None:
    """Get the type of LinkedIn URL.

    Args:
        url: LinkedIn URL to analyze.

    Returns:
        URL type: 'profile', 'job', 'company', 'school', 'post', or 'other'.
        Returns None if not a LinkedIn URL.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        if "linkedin.com" not in parsed.netloc.lower():
            return None

        path = parsed.path.rstrip("/").lower()

        if re.match(r"^/(in|pub)/", path):
            return "profile"
        elif "/jobs/" in path:
            return "job"
        elif "/company/" in path:
            return "company"
        elif "/school/" in path:
            return "school"
        elif "/posts/" in path or "/pulse/" in path:
            return "post"
        else:
            return "other"
    except Exception:
        return None


class InvalidLinkedInUrlRule(ValidationRule):
    """Flags applicants who provide non-profile LinkedIn URLs.

    This rule checks if the LinkedIn URL provided is an actual profile URL
    (/in/username or /pub/...) rather than a job posting, company page,
    or other non-profile link. Submitting a job posting URL instead of
    a profile URL may indicate a fraudulent or low-effort application.
    """

    name: str = "invalid_linkedin_url"
    description: str = "LinkedIn URL is not a valid profile URL"
    category: str = "linkedin"
    default_severity: RuleSeverity = RuleSeverity.MEDIUM
    version: str = "1.0.0"
    checks_fields: ClassVar[list[str]] = ["linkedin_url"]
    trigger_examples: ClassVar[list[str]] = [
        "LinkedIn URL is a job posting (linkedin.com/jobs/...)",
        "LinkedIn URL is a company page (linkedin.com/company/...)",
        "LinkedIn URL is a school page (linkedin.com/school/...)",
    ]
    rationale: str = (
        "Legitimate applicants typically provide their personal LinkedIn profile URL. "
        "Submitting a job posting URL or company page instead may indicate a fake, "
        "lazy, or automated application."
    )

    async def validate(self, data: dict[str, Any]) -> RuleResult:
        """Check if LinkedIn URL is a valid profile URL.

        Args:
            data: Dictionary containing applicant data with 'linkedin_url' key.

        Returns:
            RuleResult - passes if URL is a profile URL or missing, fails otherwise.
        """
        linkedin_url = data.get("linkedin_url")

        # No LinkedIn URL is not flagged by this rule (handled by a different rule)
        if not linkedin_url:
            return RuleResult.create_skip(
                self.name,
                reason="No LinkedIn URL provided",
            )

        url_type = get_linkedin_url_type(linkedin_url)

        # Valid profile URL
        if url_type == "profile":
            return RuleResult.create_pass(
                self.name,
                message="LinkedIn URL is a valid profile URL",
            )

        # Non-profile URL - flag it
        type_descriptions = {
            "job": "a job posting",
            "company": "a company page",
            "school": "a school page",
            "post": "a post/article",
            "other": "not a profile page",
        }

        description = type_descriptions.get(url_type or "other", "not a profile page")

        return RuleResult.create_fail(
            self.name,
            message=f"LinkedIn URL is {description}, not a personal profile",
            severity=self.default_severity,
            evidence=[
                ValidationEvidence(
                    evidence_type="linkedin_url",
                    key="url",
                    value=linkedin_url,
                    description=f"URL type: {url_type or 'unknown'}",
                ),
                ValidationEvidence(
                    evidence_type="url_type",
                    key="type",
                    value=url_type or "unknown",
                    description="Type of LinkedIn URL detected",
                ),
            ],
        )
