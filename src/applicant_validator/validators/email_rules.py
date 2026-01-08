"""Email validation rules."""

import logging
import re
from pathlib import Path
from typing import Any

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)

logger = logging.getLogger(__name__)

# Simple email regex for basic format validation
EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


class DisposableEmailRule(ValidationRule):
    """Validates that email is not from a known disposable email provider.

    This rule checks the email domain against a database of known disposable
    email providers. The database can be populated from external sources
    (like GitHub lists) or manually.

    Falls back to a local file if database is not available.
    """

    name = "disposable_email"
    description = "Check if email is from a disposable email provider"
    category = "email"
    default_severity = RuleSeverity.HIGH
    version = "2.0.0"  # Updated for database support
    checks_fields = ["email"]
    trigger_examples = [
        "user@mailinator.com",
        "test@guerrillamail.com",
        "temp@10minutemail.com",
    ]
    rationale = (
        "Disposable email addresses are temporary inboxes that expire after a short time. "
        "Legitimate job applicants typically use permanent email addresses. "
        "Use of disposable emails may indicate an attempt to avoid follow-up contact "
        "or hide identity."
    )

    def __init__(self) -> None:
        """Initialize the rule."""
        self._disposable_domains: set[str] | None = None
        self._use_database: bool = True

    async def _load_disposable_domains(self) -> set[str]:
        """Load disposable domains from database or fallback to file.

        Returns:
            Set of disposable domain strings.
        """
        if self._disposable_domains is not None:
            return self._disposable_domains

        # Try database first
        if self._use_database:
            try:
                from applicant_validator.services.validation_data import (
                    get_validation_data_service,
                )

                service = get_validation_data_service()
                domains = await service.get_disposable_domains()

                if domains:
                    self._disposable_domains = domains
                    logger.info(f"Loaded {len(domains)} disposable domains from database")
                    return self._disposable_domains
                else:
                    logger.warning("No domains in database, falling back to file")
            except Exception as e:
                logger.warning(f"Could not load from database, falling back to file: {e}")
                self._use_database = False

        # Fallback to file
        self._disposable_domains = self._load_from_file()
        return self._disposable_domains

    def _load_from_file(self) -> set[str]:
        """Load disposable domains from the data file (fallback)."""
        data_file = Path(__file__).parent.parent / "data" / "disposable_domains.txt"

        if not data_file.exists():
            # Fall back to a minimal set if file doesn't exist
            logger.warning("Disposable domains file not found, using minimal fallback set")
            return {
                "tempmail.com",
                "guerrillamail.com",
                "mailinator.com",
                "10minutemail.com",
                "throwaway.email",
            }

        domains: set[str] = set()
        with data_file.open(encoding="utf-8") as f:
            for raw_line in f:
                stripped = raw_line.strip()
                # Skip empty lines and comments
                if stripped and not stripped.startswith("#"):
                    domains.add(stripped.lower())

        logger.info(f"Loaded {len(domains)} disposable domains from file")
        return domains

    def _extract_domain(self, email: str) -> str | None:
        """Extract the domain from an email address."""
        if "@" not in email:
            return None
        return email.split("@")[-1].lower()

    async def _is_disposable_domain(self, domain: str) -> str | None:
        """Check if domain or any parent domain is disposable.

        Returns the matched disposable domain if found, None otherwise.
        """
        disposable_domains = await self._load_disposable_domains()

        # Check exact match
        if domain in disposable_domains:
            return domain

        # Check parent domains (for subdomains like mail.tempmail.com)
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent_domain = ".".join(parts[i:])
            if parent_domain in disposable_domains:
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
        matched_domain = await self._is_disposable_domain(domain)

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
