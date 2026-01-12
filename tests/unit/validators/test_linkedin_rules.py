"""Tests for LinkedIn validation rules."""

import pytest

from applicant_validator.validators.linkedin_rules import (
    InvalidLinkedInUrlRule,
    get_linkedin_url_type,
    is_linkedin_profile_url,
)


class TestIsLinkedInProfileUrl:
    """Tests for is_linkedin_profile_url helper function."""

    def test_valid_in_profile_url(self) -> None:
        """Should return True for /in/ profile URLs."""
        assert is_linkedin_profile_url("https://www.linkedin.com/in/johndoe")
        assert is_linkedin_profile_url("https://linkedin.com/in/john-doe-123")
        assert is_linkedin_profile_url("https://www.linkedin.com/in/johndoe/")

    def test_valid_pub_profile_url(self) -> None:
        """Should return True for /pub/ profile URLs."""
        assert is_linkedin_profile_url("https://www.linkedin.com/pub/john-doe/12/345/678")

    def test_job_url_not_profile(self) -> None:
        """Should return False for job posting URLs."""
        assert not is_linkedin_profile_url("https://www.linkedin.com/jobs/view/123456")

    def test_company_url_not_profile(self) -> None:
        """Should return False for company page URLs."""
        assert not is_linkedin_profile_url("https://www.linkedin.com/company/acme-corp")

    def test_school_url_not_profile(self) -> None:
        """Should return False for school page URLs."""
        assert not is_linkedin_profile_url("https://www.linkedin.com/school/mit")

    def test_none_url(self) -> None:
        """Should return False for None."""
        assert not is_linkedin_profile_url(None)

    def test_empty_url(self) -> None:
        """Should return False for empty string."""
        assert not is_linkedin_profile_url("")


class TestGetLinkedInUrlType:
    """Tests for get_linkedin_url_type helper function."""

    def test_profile_type_in(self) -> None:
        """Should detect /in/ profile URLs."""
        assert get_linkedin_url_type("https://www.linkedin.com/in/johndoe") == "profile"

    def test_profile_type_pub(self) -> None:
        """Should detect /pub/ profile URLs."""
        assert get_linkedin_url_type("https://www.linkedin.com/pub/john/1/2/3") == "profile"

    def test_job_type(self) -> None:
        """Should detect job posting URLs."""
        assert get_linkedin_url_type("https://www.linkedin.com/jobs/view/123456") == "job"
        assert get_linkedin_url_type("https://www.linkedin.com/jobs/search/") == "job"

    def test_company_type(self) -> None:
        """Should detect company page URLs."""
        assert get_linkedin_url_type("https://www.linkedin.com/company/google") == "company"

    def test_school_type(self) -> None:
        """Should detect school page URLs."""
        assert get_linkedin_url_type("https://www.linkedin.com/school/stanford") == "school"

    def test_post_type(self) -> None:
        """Should detect post/article URLs."""
        assert get_linkedin_url_type("https://www.linkedin.com/posts/johndoe_abc123") == "post"
        assert get_linkedin_url_type("https://www.linkedin.com/pulse/article-title") == "post"

    def test_other_type(self) -> None:
        """Should return 'other' for unknown LinkedIn paths."""
        assert get_linkedin_url_type("https://www.linkedin.com/feed") == "other"
        assert get_linkedin_url_type("https://www.linkedin.com/learning/course") == "other"

    def test_non_linkedin_url(self) -> None:
        """Should return None for non-LinkedIn URLs."""
        assert get_linkedin_url_type("https://github.com/user") is None
        assert get_linkedin_url_type("https://google.com") is None

    def test_none_url(self) -> None:
        """Should return None for None input."""
        assert get_linkedin_url_type(None) is None


class TestInvalidLinkedInUrlRule:
    """Tests for InvalidLinkedInUrlRule."""

    @pytest.fixture
    def rule(self) -> InvalidLinkedInUrlRule:
        """Create rule instance."""
        return InvalidLinkedInUrlRule()

    @pytest.mark.asyncio
    async def test_passes_for_valid_profile_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should pass for valid /in/ profile URLs."""
        result = await rule.validate({"linkedin_url": "https://www.linkedin.com/in/johndoe"})
        assert result.passed
        assert not result.was_skipped

    @pytest.mark.asyncio
    async def test_passes_for_pub_profile_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should pass for valid /pub/ profile URLs."""
        result = await rule.validate(
            {"linkedin_url": "https://www.linkedin.com/pub/john-doe/1/2/3"}
        )
        assert result.passed
        assert not result.was_skipped

    @pytest.mark.asyncio
    async def test_skips_when_no_linkedin_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should skip when no LinkedIn URL is provided."""
        result = await rule.validate({"linkedin_url": None})
        assert result.passed
        assert result.was_skipped
        assert "No LinkedIn URL" in (result.skip_reason or "")

    @pytest.mark.asyncio
    async def test_fails_for_job_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should fail for job posting URLs."""
        result = await rule.validate({"linkedin_url": "https://www.linkedin.com/jobs/view/123456"})
        assert not result.passed
        assert "job posting" in result.message.lower()
        assert result.severity is not None

    @pytest.mark.asyncio
    async def test_fails_for_company_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should fail for company page URLs."""
        result = await rule.validate({"linkedin_url": "https://www.linkedin.com/company/acme-corp"})
        assert not result.passed
        assert "company page" in result.message.lower()

    @pytest.mark.asyncio
    async def test_fails_for_school_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should fail for school page URLs."""
        result = await rule.validate({"linkedin_url": "https://www.linkedin.com/school/mit"})
        assert not result.passed
        assert "school page" in result.message.lower()

    @pytest.mark.asyncio
    async def test_fails_for_post_url(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should fail for post/article URLs."""
        result = await rule.validate(
            {"linkedin_url": "https://www.linkedin.com/posts/johndoe_abc123"}
        )
        assert not result.passed
        assert "post" in result.message.lower()

    @pytest.mark.asyncio
    async def test_provides_evidence_on_failure(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should include evidence when failing."""
        url = "https://www.linkedin.com/jobs/view/4358420429"
        result = await rule.validate({"linkedin_url": url})

        assert not result.passed
        assert len(result.evidence) >= 2

        # Check URL evidence
        url_evidence = next((e for e in result.evidence if e.evidence_type == "linkedin_url"), None)
        assert url_evidence is not None
        assert url_evidence.value == url

        # Check type evidence
        type_evidence = next((e for e in result.evidence if e.evidence_type == "url_type"), None)
        assert type_evidence is not None
        assert type_evidence.value == "job"

    @pytest.mark.asyncio
    async def test_rule_metadata(self, rule: InvalidLinkedInUrlRule) -> None:
        """Should have correct metadata."""
        assert rule.name == "invalid_linkedin_url"
        assert rule.category == "linkedin"
        assert "linkedin_url" in rule.checks_fields
