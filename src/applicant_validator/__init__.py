"""Applicant Validator - Detect fraudulent job applicants.

This package provides tools for validating job applicants by integrating
with Lever ATS and LinkedIn APIs to identify potentially fraudulent applications.
"""

from applicant_validator.config import Settings, get_settings
from applicant_validator.exceptions import (
    ApplicantNotFoundError,
    ApplicantValidatorError,
    ConfigurationError,
    LeverAPIError,
    LinkedInAPIError,
    RateLimitExceededError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "ApplicantNotFoundError",
    "ApplicantValidatorError",
    "ConfigurationError",
    "LeverAPIError",
    "LinkedInAPIError",
    "RateLimitExceededError",
    "Settings",
    "ValidationError",
    "__version__",
    "get_settings",
]
