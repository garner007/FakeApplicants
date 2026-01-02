"""Tests for Applicant model."""

from datetime import UTC, datetime

import pytest

from applicant_validator.models.applicant import Applicant
from applicant_validator.models.linkedin import Education, Experience, LinkedInProfile


class TestApplicant:
    """Tests for Applicant model."""

    def test_applicant_creation_full(self) -> None:
        """Applicant should be creatable with all fields."""
        created_at = datetime.now(UTC)
        applicant = Applicant(
            id="lever123",
            name="John Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567",
            linkedin_url="https://linkedin.com/in/johndoe",
            resume_url="https://storage.example.com/resume.pdf",
            location="San Francisco, CA",
            company="Current Corp",
            headline="Senior Software Engineer",
            sources=["LinkedIn", "Referral"],
            created_at=created_at,
            opportunity_id="opp456",
            stage="Application Review",
        )
        assert applicant.id == "lever123"
        assert applicant.name == "John Doe"
        assert applicant.email == "john.doe@example.com"
        assert applicant.phone == "+1-555-123-4567"
        assert applicant.linkedin_url == "https://linkedin.com/in/johndoe"
        assert applicant.resume_url == "https://storage.example.com/resume.pdf"
        assert applicant.location == "San Francisco, CA"
        assert applicant.company == "Current Corp"
        assert applicant.headline == "Senior Software Engineer"
        assert applicant.sources == ["LinkedIn", "Referral"]
        assert applicant.created_at == created_at
        assert applicant.opportunity_id == "opp456"
        assert applicant.stage == "Application Review"
        assert applicant.linkedin_profile is None

    def test_applicant_creation_minimal(self) -> None:
        """Applicant should be creatable with only required fields."""
        applicant = Applicant(
            id="min123",
            name="Jane Smith",
            email="jane@example.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp789",
            stage="New Application",
        )
        assert applicant.id == "min123"
        assert applicant.name == "Jane Smith"
        assert applicant.email == "jane@example.com"
        assert applicant.phone is None
        assert applicant.linkedin_url is None
        assert applicant.resume_url is None
        assert applicant.location is None
        assert applicant.company is None
        assert applicant.headline is None
        assert applicant.sources == []
        assert applicant.linkedin_profile is None

    def test_applicant_with_linkedin_profile(self) -> None:
        """Applicant should support enriched LinkedIn profile data."""
        profile = LinkedInProfile(
            id="li123",
            url="https://linkedin.com/in/johndoe",
            name="John Doe",
            headline="Senior Engineer",
            current_company="Tech Corp",
            experience=[
                Experience(
                    title="Senior Engineer",
                    company="Tech Corp",
                    is_current=True,
                )
            ],
            education=[Education(school="MIT", degree="BS")],
            skills=["Python", "AWS"],
            last_fetched=datetime.now(UTC),
        )

        applicant = Applicant(
            id="lever123",
            name="John Doe",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            created_at=datetime.now(UTC),
            opportunity_id="opp456",
            stage="Interview",
            linkedin_profile=profile,
        )

        assert applicant.linkedin_profile is not None
        assert applicant.linkedin_profile.name == "John Doe"
        assert len(applicant.linkedin_profile.experience) == 1

    def test_applicant_serialization(self) -> None:
        """Applicant should serialize to dict correctly."""
        created_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        applicant = Applicant(
            id="ser123",
            name="Serialize Test",
            email="serialize@test.com",
            phone="+1-555-999-8888",
            linkedin_url="https://linkedin.com/in/sertest",
            location="NYC",
            sources=["Indeed"],
            created_at=created_at,
            opportunity_id="opp999",
            stage="Screening",
        )

        data = applicant.model_dump()
        assert data["id"] == "ser123"
        assert data["name"] == "Serialize Test"
        assert data["email"] == "serialize@test.com"
        assert data["phone"] == "+1-555-999-8888"
        assert data["linkedin_url"] == "https://linkedin.com/in/sertest"
        assert data["sources"] == ["Indeed"]
        assert data["linkedin_profile"] is None

    def test_applicant_serialization_with_linkedin(self) -> None:
        """Applicant should serialize LinkedIn profile correctly."""
        profile = LinkedInProfile(
            id="li_ser",
            url="https://linkedin.com/in/sertest",
            name="Serialize Test",
            last_fetched=datetime.now(UTC),
        )

        applicant = Applicant(
            id="ser456",
            name="Serialize Test",
            email="ser@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp111",
            stage="Applied",
            linkedin_profile=profile,
        )

        data = applicant.model_dump()
        assert data["linkedin_profile"] is not None
        assert data["linkedin_profile"]["id"] == "li_ser"
        assert data["linkedin_profile"]["name"] == "Serialize Test"

    def test_applicant_deserialization(self) -> None:
        """Applicant should deserialize from dict correctly."""
        data = {
            "id": "deser123",
            "name": "Deser Test",
            "email": "deser@test.com",
            "phone": "+1-555-111-2222",
            "linkedin_url": "https://linkedin.com/in/desertest",
            "resume_url": "https://storage.example.com/resume.pdf",
            "location": "Boston",
            "company": "Deser Corp",
            "headline": "Software Developer",
            "sources": ["LinkedIn", "Website"],
            "created_at": "2024-01-15T12:00:00Z",
            "opportunity_id": "opp_deser",
            "stage": "Phone Screen",
        }

        applicant = Applicant.model_validate(data)
        assert applicant.id == "deser123"
        assert applicant.name == "Deser Test"
        assert applicant.company == "Deser Corp"
        assert len(applicant.sources) == 2

    def test_applicant_deserialization_with_linkedin(self) -> None:
        """Applicant should deserialize with nested LinkedIn profile."""
        data = {
            "id": "nested123",
            "name": "Nested Test",
            "email": "nested@test.com",
            "created_at": "2024-01-15T12:00:00Z",
            "opportunity_id": "opp_nested",
            "stage": "Applied",
            "linkedin_profile": {
                "id": "li_nested",
                "url": "https://linkedin.com/in/nestedtest",
                "name": "Nested Test",
                "headline": "Developer",
                "experience": [{"title": "Dev", "company": "Test Co", "is_current": True}],
                "last_fetched": "2024-01-15T12:00:00Z",
            },
        }

        applicant = Applicant.model_validate(data)
        assert applicant.linkedin_profile is not None
        assert applicant.linkedin_profile.headline == "Developer"
        assert len(applicant.linkedin_profile.experience) == 1

    def test_applicant_has_linkedin_url(self) -> None:
        """Applicant should check if LinkedIn URL exists."""
        with_url = Applicant(
            id="url123",
            name="Has URL",
            email="url@test.com",
            linkedin_url="https://linkedin.com/in/hasurl",
            created_at=datetime.now(UTC),
            opportunity_id="opp_url",
            stage="Applied",
        )
        assert with_url.has_linkedin_url is True

        without_url = Applicant(
            id="nourl123",
            name="No URL",
            email="nourl@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_nourl",
            stage="Applied",
        )
        assert without_url.has_linkedin_url is False

    def test_applicant_is_enriched(self) -> None:
        """Applicant should check if LinkedIn profile is enriched."""
        profile = LinkedInProfile(
            id="li_enrich",
            url="https://linkedin.com/in/enriched",
            name="Enriched",
            last_fetched=datetime.now(UTC),
        )

        enriched = Applicant(
            id="enr123",
            name="Enriched",
            email="enriched@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_enr",
            stage="Applied",
            linkedin_profile=profile,
        )
        assert enriched.is_enriched is True

        not_enriched = Applicant(
            id="notenr123",
            name="Not Enriched",
            email="notenriched@test.com",
            linkedin_url="https://linkedin.com/in/notenriched",
            created_at=datetime.now(UTC),
            opportunity_id="opp_notenr",
            stage="Applied",
        )
        assert not_enriched.is_enriched is False

    def test_applicant_first_name(self) -> None:
        """Applicant should extract first name."""
        applicant = Applicant(
            id="fn123",
            name="John Michael Doe",
            email="john@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_fn",
            stage="Applied",
        )
        assert applicant.first_name == "John"

        single_name = Applicant(
            id="sn123",
            name="Madonna",
            email="madonna@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_sn",
            stage="Applied",
        )
        assert single_name.first_name == "Madonna"

    def test_applicant_last_name(self) -> None:
        """Applicant should extract last name."""
        applicant = Applicant(
            id="ln123",
            name="John Michael Doe",
            email="john@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_ln",
            stage="Applied",
        )
        assert applicant.last_name == "Doe"

        single_name = Applicant(
            id="sln123",
            name="Madonna",
            email="madonna@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_sln",
            stage="Applied",
        )
        assert single_name.last_name is None

    def test_applicant_email_domain(self) -> None:
        """Applicant should extract email domain."""
        applicant = Applicant(
            id="ed123",
            name="Email Test",
            email="john.doe@example.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_ed",
            stage="Applied",
        )
        assert applicant.email_domain == "example.com"

    def test_applicant_empty_sources_default(self) -> None:
        """Applicant should default to empty sources list."""
        applicant = Applicant(
            id="src123",
            name="Sources Test",
            email="sources@test.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_src",
            stage="Applied",
        )
        assert applicant.sources == []

    def test_applicant_email_validation(self) -> None:
        """Applicant should validate email format."""
        # Valid email
        applicant = Applicant(
            id="email123",
            name="Email Test",
            email="valid.email@domain.com",
            created_at=datetime.now(UTC),
            opportunity_id="opp_email",
            stage="Applied",
        )
        assert applicant.email == "valid.email@domain.com"

        # Invalid email should raise
        with pytest.raises(ValueError):
            Applicant(
                id="bad_email",
                name="Bad Email",
                email="not-an-email",
                created_at=datetime.now(UTC),
                opportunity_id="opp_bad",
                stage="Applied",
            )

    def test_applicant_linkedin_url_validation(self) -> None:
        """Applicant should validate LinkedIn URL format."""
        # Valid LinkedIn URLs
        valid_urls = [
            "https://linkedin.com/in/johndoe",
            "https://www.linkedin.com/in/johndoe",
            "http://linkedin.com/in/johndoe",
            "https://linkedin.com/in/john-doe-123",
        ]

        for url in valid_urls:
            applicant = Applicant(
                id="li_valid",
                name="LinkedIn Test",
                email="li@test.com",
                linkedin_url=url,
                created_at=datetime.now(UTC),
                opportunity_id="opp_li",
                stage="Applied",
            )
            assert applicant.linkedin_url == url

    def test_applicant_model_copy(self) -> None:
        """Applicant should support model copy with updates."""
        original = Applicant(
            id="copy123",
            name="Copy Test",
            email="copy@test.com",
            stage="Applied",
            created_at=datetime.now(UTC),
            opportunity_id="opp_copy",
        )

        updated = original.model_copy(update={"stage": "Interview"})
        assert updated.stage == "Interview"
        assert updated.id == original.id
        assert original.stage == "Applied"  # Original unchanged
