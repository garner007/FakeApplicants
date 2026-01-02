"""Applicant data model from Lever ATS."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from applicant_validator.models.linkedin import LinkedInProfile


class Applicant(BaseModel):
    """Applicant data from Lever ATS with optional LinkedIn enrichment."""

    id: str = Field(..., description="Lever applicant/candidate ID")
    name: str = Field(..., description="Full name of the applicant")
    email: str = Field(..., description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    linkedin_url: str | None = Field(default=None, description="LinkedIn profile URL")
    resume_url: str | None = Field(default=None, description="URL to resume/CV")
    location: str | None = Field(default=None, description="Location from application")
    company: str | None = Field(default=None, description="Current/most recent company")
    headline: str | None = Field(default=None, description="Professional headline")
    sources: list[str] = Field(
        default_factory=list, description="Application sources (e.g., LinkedIn, Referral)"
    )
    created_at: datetime = Field(..., description="When application was created")
    opportunity_id: str = Field(..., description="Lever opportunity/job ID")
    stage: str = Field(..., description="Current stage in hiring pipeline")

    # Enriched data from LinkedIn
    linkedin_profile: LinkedInProfile | None = Field(
        default=None, description="Enriched LinkedIn profile data"
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        # Basic email validation pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            msg = "Invalid email format"
            raise ValueError(msg)
        return v

    @property
    def has_linkedin_url(self) -> bool:
        """Check if applicant has a LinkedIn URL."""
        return self.linkedin_url is not None

    @property
    def is_enriched(self) -> bool:
        """Check if applicant has been enriched with LinkedIn data."""
        return self.linkedin_profile is not None

    @property
    def first_name(self) -> str:
        """Extract first name from full name."""
        parts = self.name.split()
        return parts[0] if parts else ""

    @property
    def last_name(self) -> str | None:
        """Extract last name from full name."""
        parts = self.name.split()
        return parts[-1] if len(parts) > 1 else None

    @property
    def email_domain(self) -> str:
        """Extract domain from email address."""
        return self.email.split("@")[1]
