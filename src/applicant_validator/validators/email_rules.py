"""Email validation rules."""

import re
from pathlib import Path
from typing import Any

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)

# Simple email regex for basic format validation
EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


class DisposableEmailRule(ValidationRule):
    """Validates that email is not from a known disposable email provider.

    This rule checks the email domain against a list of known disposable
    email providers. These are temporary email services often used to
    avoid spam or verification.
    """

    name = "disposable_email"
    description = "Check if email is from a disposable email provider"
    category = "email"
    default_severity = RuleSeverity.HIGH
    version = "1.0.0"

    def __init__(self) -> None:
        """Initialize the rule and load disposable domains."""
        self._disposable_domains: set[str] = set()
        self._load_disposable_domains()

    def _load_disposable_domains(self) -> None:
        """Load disposable domains from the data file."""
        data_file = Path(__file__).parent.parent / "data" / "disposable_domains.txt"

        if not data_file.exists():
            # Fall back to a minimal set if file doesn't exist
            self._disposable_domains = {
                "tempmail.com",
                "guerrillamail.com",
                "mailinator.com",
                "10minutemail.com",
                "throwaway.email",
            }
            return

        with data_file.open(encoding="utf-8") as f:
            for raw_line in f:
                stripped = raw_line.strip()
                # Skip empty lines and comments
                if stripped and not stripped.startswith("#"):
                    self._disposable_domains.add(stripped.lower())

    def _extract_domain(self, email: str) -> str | None:
        """Extract the domain from an email address."""
        if "@" not in email:
            return None
        return email.split("@")[-1].lower()

    def _is_disposable_domain(self, domain: str) -> str | None:
        """Check if domain or any parent domain is disposable.

        Returns the matched disposable domain if found, None otherwise.
        """
        # Check exact match
        if domain in self._disposable_domains:
            return domain

        # Check parent domains (for subdomains like mail.tempmail.com)
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent_domain = ".".join(parts[i:])
            if parent_domain in self._disposable_domains:
                return parent_domain

        return None

    async def validate(self, data: dict[str, Any]) -> RuleResult:
        """Validate that the email is not from a disposable provider.

        Args:
            data: Dictionary containing 'email' key.

        Returns:
            RuleResult with pass/fail status and evidence.
        """
        email = data.get("email")

        # Handle missing or empty email
        if not email:
            return RuleResult.create_skip(self.name, "No email provided")

        email = str(email).strip()
        if not email:
            return RuleResult.create_skip(self.name, "Empty email provided")

        # Basic format check - skip if invalid format
        if not EMAIL_PATTERN.match(email):
            return RuleResult.create_skip(
                self.name, "Invalid email format - skipping disposable check"
            )

        # Extract domain
        domain = self._extract_domain(email)
        if not domain:
            return RuleResult.create_skip(self.name, "Could not extract domain from email")

        # Check against disposable domains
        matched_domain = self._is_disposable_domain(domain)

        if matched_domain:
            return RuleResult.create_fail(
                rule_name=self.name,
                message=f"Email uses disposable domain: {matched_domain}",
                severity=self.default_severity,
                evidence=[
                    ValidationEvidence(
                        evidence_type="matched_domain",
                        key="domain",
                        value=matched_domain,
                        description=(
                            f"Domain '{domain}' matches known "
                            f"disposable provider '{matched_domain}'"
                        ),
                    ),
                    ValidationEvidence(
                        evidence_type="input_value",
                        key="email",
                        value=email,
                        description="The email address that was validated",
                    ),
                ],
            )

        return RuleResult.create_pass(self.name, f"Email domain '{domain}' is not disposable")
