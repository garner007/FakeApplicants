"""LinkedIn profile and related data models."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class Experience(BaseModel):
    """Work experience entry from LinkedIn profile."""

    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str | None = Field(default=None, description="Work location")
    start_date: date | None = Field(default=None, description="Start date of position")
    end_date: date | None = Field(default=None, description="End date of position")
    description: str | None = Field(default=None, description="Job description")
    is_current: bool = Field(default=False, description="Whether this is current position")

    @property
    def duration_months(self) -> int | None:
        """Calculate duration in months.

        Returns None if start_date is not available.
        For current positions, calculates duration to today.
        """
        if self.start_date is None:
            return None

        end = self.end_date if not self.is_current else date.today()
        if end is None:
            end = date.today()

        months = (end.year - self.start_date.year) * 12
        months += end.month - self.start_date.month
        return max(0, months)


class Education(BaseModel):
    """Education entry from LinkedIn profile."""

    school: str = Field(..., description="School or institution name")
    degree: str | None = Field(default=None, description="Degree obtained")
    field_of_study: str | None = Field(default=None, description="Field or major")
    start_date: date | None = Field(default=None, description="Start date")
    end_date: date | None = Field(default=None, description="End date or graduation")
    description: str | None = Field(default=None, description="Additional details")


class LinkedInProfile(BaseModel):
    """LinkedIn profile data model."""

    id: str = Field(..., description="LinkedIn profile ID")
    url: str = Field(..., description="LinkedIn profile URL")
    name: str = Field(..., description="Full name on profile")
    headline: str | None = Field(default=None, description="Professional headline")
    location: str | None = Field(default=None, description="Location from profile")
    current_company: str | None = Field(default=None, description="Current employer")
    connections_count: int | None = Field(default=None, description="Number of connections")
    profile_picture_url: str | None = Field(default=None, description="URL to profile picture")
    experience: list[Experience] = Field(
        default_factory=list, description="Work experience entries"
    )
    education: list[Education] = Field(default_factory=list, description="Education entries")
    skills: list[str] = Field(default_factory=list, description="Listed skills")
    is_public: bool = Field(default=True, description="Whether profile is public")
    last_fetched: datetime = Field(..., description="When profile was last fetched")

    @property
    def has_profile_picture(self) -> bool:
        """Check if profile has a profile picture."""
        return self.profile_picture_url is not None

    @property
    def total_experience_months(self) -> int:
        """Calculate total months of work experience."""
        total = 0
        for exp in self.experience:
            if exp.duration_months is not None:
                total += exp.duration_months
        return total

    @property
    def earliest_experience_date(self) -> date | None:
        """Find the earliest experience start date."""
        dates = [exp.start_date for exp in self.experience if exp.start_date is not None]
        return min(dates) if dates else None
