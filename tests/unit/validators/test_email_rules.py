"""Tests for email validation rules."""

import pytest

from applicant_validator.validators.base import RuleSeverity
from applicant_validator.validators.email_rules import DisposableEmailRule


class TestDisposableEmailRule:
    """Tests for the DisposableEmailRule validator."""

    @pytest.fixture
    def rule(self) -> DisposableEmailRule:
        """Create a DisposableEmailRule instance."""
        return DisposableEmailRule()

    async def test_valid_email_passes(self, rule: DisposableEmailRule) -> None:
        """Valid email from legitimate domain should pass."""
        result = await rule.validate({"email": "john.doe@gmail.com"})

        assert result.passed is True
        assert result.rule_name == "disposable_email"
        assert result.was_skipped is False

    async def test_disposable_email_fails(self, rule: DisposableEmailRule) -> None:
        """Email from known disposable domain should fail."""
        result = await rule.validate({"email": "test@tempmail.com"})

        assert result.passed is False
        assert result.severity == RuleSeverity.HIGH
        assert "disposable" in result.message.lower()
        assert len(result.evidence) > 0
        assert result.evidence[0].evidence_type == "matched_domain"

    async def test_disposable_email_guerrillamail(self, rule: DisposableEmailRule) -> None:
        """Email from guerrillamail should fail."""
        result = await rule.validate({"email": "user@guerrillamail.com"})

        assert result.passed is False
        assert "guerrillamail.com" in result.evidence[0].value

    async def test_disposable_email_mailinator(self, rule: DisposableEmailRule) -> None:
        """Email from mailinator should fail."""
        result = await rule.validate({"email": "test@mailinator.com"})

        assert result.passed is False

    async def test_disposable_email_10minutemail(self, rule: DisposableEmailRule) -> None:
        """Email from 10minutemail should fail."""
        result = await rule.validate({"email": "user@10minutemail.com"})

        assert result.passed is False

    async def test_corporate_email_passes(self, rule: DisposableEmailRule) -> None:
        """Email from corporate domain should pass."""
        result = await rule.validate({"email": "jane@acme-corp.com"})

        assert result.passed is True

    async def test_common_providers_pass(self, rule: DisposableEmailRule) -> None:
        """Common email providers should pass."""
        providers = [
            "user@gmail.com",
            "user@yahoo.com",
            "user@outlook.com",
            "user@hotmail.com",
            "user@icloud.com",
            "user@protonmail.com",
        ]

        for email in providers:
            result = await rule.validate({"email": email})
            assert result.passed is True, f"{email} should pass"

    async def test_case_insensitive_matching(self, rule: DisposableEmailRule) -> None:
        """Domain matching should be case-insensitive."""
        result = await rule.validate({"email": "test@TEMPMAIL.COM"})

        assert result.passed is False

    async def test_subdomain_of_disposable_fails(self, rule: DisposableEmailRule) -> None:
        """Subdomain of known disposable domain should also fail."""
        result = await rule.validate({"email": "test@mail.tempmail.com"})

        assert result.passed is False

    async def test_missing_email_skips(self, rule: DisposableEmailRule) -> None:
        """Missing email field should skip validation."""
        result = await rule.validate({})

        assert result.passed is True
        assert result.was_skipped is True
        assert "email" in result.skip_reason.lower()

    async def test_empty_email_skips(self, rule: DisposableEmailRule) -> None:
        """Empty email should skip validation."""
        result = await rule.validate({"email": ""})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_none_email_skips(self, rule: DisposableEmailRule) -> None:
        """None email should skip validation."""
        result = await rule.validate({"email": None})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_invalid_email_format_skips(self, rule: DisposableEmailRule) -> None:
        """Invalid email format should skip (let format validator handle it)."""
        result = await rule.validate({"email": "not-an-email"})

        assert result.passed is True
        assert result.was_skipped is True
        assert "format" in result.skip_reason.lower()

    async def test_rule_metadata(self, rule: DisposableEmailRule) -> None:
        """Rule should have correct metadata."""
        assert rule.name == "disposable_email"
        assert rule.category == "email"
        assert rule.default_severity == RuleSeverity.HIGH
        assert rule.version is not None

    async def test_evidence_contains_domain(self, rule: DisposableEmailRule) -> None:
        """Evidence should contain the matched disposable domain."""
        result = await rule.validate({"email": "user@throwaway.email"})

        assert result.passed is False
        assert len(result.evidence) >= 1

        domain_evidence = next(
            (e for e in result.evidence if e.evidence_type == "matched_domain"), None
        )
        assert domain_evidence is not None
        assert "throwaway.email" in domain_evidence.value

    async def test_loads_disposable_domains_from_file(self, rule: DisposableEmailRule) -> None:
        """Rule should load disposable domains from data file."""
        # Trigger lazy loading by calling the internal method
        domains = await rule._load_disposable_domains()
        assert len(domains) > 100  # We have ~1000 domains
