"""Custom exceptions for the Applicant Validator application.

This module defines a hierarchy of exceptions for different error scenarios
in the application, enabling precise error handling and informative error messages.
"""

from typing import Any


class ApplicantValidatorError(Exception):
    """Base exception for all Applicant Validator errors.

    All custom exceptions in this application inherit from this class,
    making it easy to catch all application-specific errors.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ConfigurationError(ApplicantValidatorError):
    """Raised when there's a configuration or setup error.

    Examples:
        - Missing required environment variables
        - Invalid configuration values
        - Failed to initialize services
    """


class LeverAPIError(ApplicantValidatorError):
    """Raised when Lever API operations fail.

    Attributes:
        status_code: HTTP status code from Lever API (if applicable).
        retry_after: Seconds to wait before retrying (for rate limits).
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Lever API error.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the API response.
            retry_after: Seconds to wait before retrying (for 429 errors).
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.status_code = status_code
        self.retry_after = retry_after


class LinkedInAPIError(ApplicantValidatorError):
    """Raised when LinkedIn API operations fail.

    Attributes:
        status_code: HTTP status code from LinkedIn API (if applicable).
        error_code: LinkedIn-specific error code.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize LinkedIn API error.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code from the API response.
            error_code: LinkedIn-specific error code.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.status_code = status_code
        self.error_code = error_code


class ValidationError(ApplicantValidatorError):
    """Raised when validation processing encounters an error.

    This is distinct from Pydantic's ValidationError and is used for
    errors in the validation rule execution pipeline.

    Attributes:
        rule_name: Name of the validation rule that failed.
    """

    def __init__(
        self,
        message: str,
        rule_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message.
            rule_name: Name of the validation rule that encountered the error.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.rule_name = rule_name


class ApplicantNotFoundError(ApplicantValidatorError):
    """Raised when an applicant cannot be found.

    Attributes:
        applicant_id: The ID of the applicant that was not found.
    """

    def __init__(
        self,
        applicant_id: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize applicant not found error.

        Args:
            applicant_id: The ID of the applicant that was not found.
            message: Optional custom message (defaults to standard message).
            details: Optional dictionary with additional error context.
        """
        msg = message or f"Applicant not found: {applicant_id}"
        super().__init__(msg, details)
        self.applicant_id = applicant_id


class RateLimitExceededError(ApplicantValidatorError):
    """Raised when API rate limits are exceeded.

    Attributes:
        service: Name of the service that rate limited the request.
        retry_after: Seconds to wait before retrying.
    """

    def __init__(
        self,
        service: str,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize rate limit error.

        Args:
            service: Name of the service (e.g., "Lever", "LinkedIn").
            retry_after: Seconds to wait before retrying.
            details: Optional dictionary with additional error context.
        """
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f". Retry after {retry_after} seconds."
        super().__init__(message, details)
        self.service = service
        self.retry_after = retry_after
