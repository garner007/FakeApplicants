"""Tests for custom exceptions."""

import pytest

from applicant_validator.exceptions import (
    ApplicantNotFoundError,
    ApplicantValidatorError,
    ConfigurationError,
    LeverAPIError,
    LinkedInAPIError,
    RateLimitExceededError,
    ValidationError,
)


class TestApplicantValidatorError:
    """Tests for the base exception class."""

    def test_basic_exception(self) -> None:
        """Base exception should store message."""
        error = ApplicantValidatorError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_exception_with_details(self) -> None:
        """Base exception should include details in string representation."""
        details = {"key": "value", "count": 42}
        error = ApplicantValidatorError("Error occurred", details=details)
        assert "Error occurred" in str(error)
        assert "key" in str(error)
        assert error.details == details


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_inherits_from_base(self) -> None:
        """ConfigurationError should inherit from ApplicantValidatorError."""
        error = ConfigurationError("Missing API key")
        assert isinstance(error, ApplicantValidatorError)

    def test_can_be_caught_as_base(self) -> None:
        """ConfigurationError should be catchable as base exception."""
        with pytest.raises(ApplicantValidatorError):
            raise ConfigurationError("Config error")


class TestLeverAPIError:
    """Tests for LeverAPIError."""

    def test_basic_error(self) -> None:
        """LeverAPIError should store message and optional attributes."""
        error = LeverAPIError("Failed to fetch")
        assert error.message == "Failed to fetch"
        assert error.status_code is None
        assert error.retry_after is None

    def test_with_status_code(self) -> None:
        """LeverAPIError should store status code."""
        error = LeverAPIError("Not found", status_code=404)
        assert error.status_code == 404

    def test_with_retry_after(self) -> None:
        """LeverAPIError should store retry_after for rate limits."""
        error = LeverAPIError("Rate limited", status_code=429, retry_after=60)
        assert error.status_code == 429
        assert error.retry_after == 60


class TestLinkedInAPIError:
    """Tests for LinkedInAPIError."""

    def test_basic_error(self) -> None:
        """LinkedInAPIError should store message and optional attributes."""
        error = LinkedInAPIError("Auth failed")
        assert error.message == "Auth failed"
        assert error.status_code is None
        assert error.error_code is None

    def test_with_error_code(self) -> None:
        """LinkedInAPIError should store LinkedIn-specific error code."""
        error = LinkedInAPIError("Access denied", status_code=403, error_code="ACCESS_DENIED")
        assert error.status_code == 403
        assert error.error_code == "ACCESS_DENIED"


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_error(self) -> None:
        """ValidationError should store message."""
        error = ValidationError("Validation failed")
        assert error.message == "Validation failed"
        assert error.rule_name is None

    def test_with_rule_name(self) -> None:
        """ValidationError should store rule name."""
        error = ValidationError("Rule execution failed", rule_name="linkedin_exists")
        assert error.rule_name == "linkedin_exists"


class TestApplicantNotFoundError:
    """Tests for ApplicantNotFoundError."""

    def test_default_message(self) -> None:
        """ApplicantNotFoundError should generate default message."""
        error = ApplicantNotFoundError("abc123")
        assert "abc123" in str(error)
        assert error.applicant_id == "abc123"

    def test_custom_message(self) -> None:
        """ApplicantNotFoundError should accept custom message."""
        error = ApplicantNotFoundError("abc123", message="Custom not found message")
        assert str(error) == "Custom not found message"
        assert error.applicant_id == "abc123"


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError."""

    def test_basic_error(self) -> None:
        """RateLimitExceededError should include service name."""
        error = RateLimitExceededError("Lever")
        assert "Lever" in str(error)
        assert error.service == "Lever"
        assert error.retry_after is None

    def test_with_retry_after(self) -> None:
        """RateLimitExceededError should include retry information."""
        error = RateLimitExceededError("LinkedIn", retry_after=30)
        assert "LinkedIn" in str(error)
        assert "30 seconds" in str(error)
        assert error.retry_after == 30
