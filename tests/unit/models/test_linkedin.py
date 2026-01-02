"""Tests for LinkedIn-related models (Experience, Education, LinkedInProfile)."""

from datetime import UTC, date, datetime

import pytest

from applicant_validator.models.linkedin import (
    Education,
    Experience,
    LinkedInProfile,
)


class TestExperience:
    """Tests for Experience model."""

    def test_experience_creation_full(self) -> None:
        """Experience should be creatable with all fields."""
        exp = Experience(
            title="Senior Software Engineer",
            company="Acme Corp",
            location="San Francisco, CA",
            start_date=date(2020, 1, 15),
            end_date=date(2023, 6, 30),
            description="Led backend development team",
            is_current=False,
        )
        assert exp.title == "Senior Software Engineer"
        assert exp.company == "Acme Corp"
        assert exp.location == "San Francisco, CA"
        assert exp.start_date == date(2020, 1, 15)
        assert exp.end_date == date(2023, 6, 30)
        assert exp.description == "Led backend development team"
        assert exp.is_current is False

    def test_experience_creation_minimal(self) -> None:
        """Experience should be creatable with only required fields."""
        exp = Experience(
            title="Software Engineer",
            company="Startup Inc",
        )
        assert exp.title == "Software Engineer"
        assert exp.company == "Startup Inc"
        assert exp.location is None
        assert exp.start_date is None
        assert exp.end_date is None
        assert exp.description is None
        assert exp.is_current is False

    def test_experience_current_position(self) -> None:
        """Experience should support current positions without end date."""
        exp = Experience(
            title="CTO",
            company="Tech Startup",
            start_date=date(2022, 3, 1),
            is_current=True,
        )
        assert exp.is_current is True
        assert exp.end_date is None

    def test_experience_serialization(self) -> None:
        """Experience should serialize to dict correctly."""
        exp = Experience(
            title="Developer",
            company="Test Co",
            start_date=date(2021, 1, 1),
            end_date=date(2022, 12, 31),
        )
        data = exp.model_dump()
        assert data["title"] == "Developer"
        assert data["company"] == "Test Co"
        assert data["start_date"] == date(2021, 1, 1)
        assert data["end_date"] == date(2022, 12, 31)

    def test_experience_deserialization(self) -> None:
        """Experience should deserialize from dict correctly."""
        data = {
            "title": "Manager",
            "company": "Big Corp",
            "location": "New York",
            "start_date": "2019-06-01",
            "end_date": "2021-05-31",
            "description": "Managed engineering team",
            "is_current": False,
        }
        exp = Experience.model_validate(data)
        assert exp.title == "Manager"
        assert exp.start_date == date(2019, 6, 1)

    def test_experience_duration_property(self) -> None:
        """Experience should calculate duration in months."""
        exp = Experience(
            title="Developer",
            company="Test Co",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
        )
        assert exp.duration_months == 12

    def test_experience_duration_current_position(self) -> None:
        """Experience duration should handle current positions."""
        exp = Experience(
            title="Developer",
            company="Test Co",
            start_date=date(2020, 1, 1),
            is_current=True,
        )
        # Duration should be calculated from start to now
        assert exp.duration_months is not None
        assert exp.duration_months > 0

    def test_experience_duration_no_dates(self) -> None:
        """Experience duration should be None when dates are missing."""
        exp = Experience(
            title="Developer",
            company="Test Co",
        )
        assert exp.duration_months is None


class TestEducation:
    """Tests for Education model."""

    def test_education_creation_full(self) -> None:
        """Education should be creatable with all fields."""
        edu = Education(
            school="Stanford University",
            degree="Bachelor of Science",
            field_of_study="Computer Science",
            start_date=date(2015, 9, 1),
            end_date=date(2019, 6, 15),
            description="Graduated with honors",
        )
        assert edu.school == "Stanford University"
        assert edu.degree == "Bachelor of Science"
        assert edu.field_of_study == "Computer Science"
        assert edu.start_date == date(2015, 9, 1)
        assert edu.end_date == date(2019, 6, 15)
        assert edu.description == "Graduated with honors"

    def test_education_creation_minimal(self) -> None:
        """Education should be creatable with only required fields."""
        edu = Education(school="MIT")
        assert edu.school == "MIT"
        assert edu.degree is None
        assert edu.field_of_study is None
        assert edu.start_date is None
        assert edu.end_date is None
        assert edu.description is None

    def test_education_serialization(self) -> None:
        """Education should serialize to dict correctly."""
        edu = Education(
            school="Harvard",
            degree="MBA",
            field_of_study="Business Administration",
        )
        data = edu.model_dump()
        assert data["school"] == "Harvard"
        assert data["degree"] == "MBA"
        assert data["field_of_study"] == "Business Administration"

    def test_education_deserialization(self) -> None:
        """Education should deserialize from dict correctly."""
        data = {
            "school": "UC Berkeley",
            "degree": "Ph.D.",
            "field_of_study": "Artificial Intelligence",
            "start_date": "2016-08-01",
            "end_date": "2021-05-15",
        }
        edu = Education.model_validate(data)
        assert edu.school == "UC Berkeley"
        assert edu.degree == "Ph.D."
        assert edu.end_date == date(2021, 5, 15)


class TestLinkedInProfile:
    """Tests for LinkedInProfile model."""

    @pytest.fixture
    def sample_experience(self) -> Experience:
        """Create sample experience for testing."""
        return Experience(
            title="Senior Developer",
            company="Tech Corp",
            start_date=date(2020, 1, 1),
            is_current=True,
        )

    @pytest.fixture
    def sample_education(self) -> Education:
        """Create sample education for testing."""
        return Education(
            school="State University",
            degree="B.S.",
            field_of_study="Computer Science",
        )

    def test_linkedin_profile_creation_full(
        self, sample_experience: Experience, sample_education: Education
    ) -> None:
        """LinkedInProfile should be creatable with all fields."""
        last_fetched = datetime.now(UTC)
        profile = LinkedInProfile(
            id="linkedin123",
            url="https://linkedin.com/in/johndoe",
            name="John Doe",
            headline="Senior Software Engineer at Tech Corp",
            location="San Francisco Bay Area",
            current_company="Tech Corp",
            connections_count=500,
            profile_picture_url="https://linkedin.com/photo/johndoe.jpg",
            experience=[sample_experience],
            education=[sample_education],
            skills=["Python", "JavaScript", "AWS"],
            is_public=True,
            last_fetched=last_fetched,
        )
        assert profile.id == "linkedin123"
        assert profile.url == "https://linkedin.com/in/johndoe"
        assert profile.name == "John Doe"
        assert profile.headline == "Senior Software Engineer at Tech Corp"
        assert profile.location == "San Francisco Bay Area"
        assert profile.current_company == "Tech Corp"
        assert profile.connections_count == 500
        assert len(profile.experience) == 1
        assert len(profile.education) == 1
        assert len(profile.skills) == 3
        assert profile.is_public is True
        assert profile.last_fetched == last_fetched

    def test_linkedin_profile_creation_minimal(self) -> None:
        """LinkedInProfile should be creatable with only required fields."""
        profile = LinkedInProfile(
            id="abc123",
            url="https://linkedin.com/in/janedoe",
            name="Jane Doe",
            last_fetched=datetime.now(UTC),
        )
        assert profile.id == "abc123"
        assert profile.name == "Jane Doe"
        assert profile.headline is None
        assert profile.location is None
        assert profile.current_company is None
        assert profile.connections_count is None
        assert profile.profile_picture_url is None
        assert profile.experience == []
        assert profile.education == []
        assert profile.skills == []
        assert profile.is_public is True

    def test_linkedin_profile_multiple_experiences(self) -> None:
        """LinkedInProfile should support multiple experiences."""
        experiences = [
            Experience(title="CEO", company="Startup", is_current=True),
            Experience(title="CTO", company="Previous Co"),
            Experience(title="Developer", company="First Job"),
        ]
        profile = LinkedInProfile(
            id="multi123",
            url="https://linkedin.com/in/founder",
            name="Founder Name",
            experience=experiences,
            last_fetched=datetime.now(UTC),
        )
        assert len(profile.experience) == 3
        assert profile.experience[0].title == "CEO"

    def test_linkedin_profile_private(self) -> None:
        """LinkedInProfile should support private profiles."""
        profile = LinkedInProfile(
            id="private123",
            url="https://linkedin.com/in/private",
            name="Private Person",
            is_public=False,
            last_fetched=datetime.now(UTC),
        )
        assert profile.is_public is False

    def test_linkedin_profile_serialization(
        self, sample_experience: Experience, sample_education: Education
    ) -> None:
        """LinkedInProfile should serialize to dict correctly."""
        last_fetched = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        profile = LinkedInProfile(
            id="ser123",
            url="https://linkedin.com/in/test",
            name="Test User",
            headline="Developer",
            experience=[sample_experience],
            education=[sample_education],
            skills=["Python"],
            last_fetched=last_fetched,
        )
        data = profile.model_dump()
        assert data["id"] == "ser123"
        assert data["name"] == "Test User"
        assert len(data["experience"]) == 1
        assert len(data["education"]) == 1
        assert data["skills"] == ["Python"]

    def test_linkedin_profile_deserialization(self) -> None:
        """LinkedInProfile should deserialize from dict correctly."""
        data = {
            "id": "deser123",
            "url": "https://linkedin.com/in/deser",
            "name": "Deser User",
            "headline": "Manager",
            "location": "NYC",
            "current_company": "Big Corp",
            "connections_count": 1000,
            "experience": [{"title": "Manager", "company": "Big Corp", "is_current": True}],
            "education": [{"school": "NYU", "degree": "MBA"}],
            "skills": ["Leadership", "Strategy"],
            "is_public": True,
            "last_fetched": "2024-01-15T12:00:00Z",
        }
        profile = LinkedInProfile.model_validate(data)
        assert profile.id == "deser123"
        assert profile.current_company == "Big Corp"
        assert profile.connections_count == 1000
        assert len(profile.experience) == 1
        assert profile.experience[0].title == "Manager"

    def test_linkedin_profile_url_validation(self) -> None:
        """LinkedInProfile should validate LinkedIn URL format."""
        # Valid URLs
        profile = LinkedInProfile(
            id="url123",
            url="https://linkedin.com/in/validuser",
            name="Valid User",
            last_fetched=datetime.now(UTC),
        )
        assert "linkedin.com" in profile.url

        # Also valid with www
        profile_www = LinkedInProfile(
            id="url456",
            url="https://www.linkedin.com/in/validuser",
            name="Valid User",
            last_fetched=datetime.now(UTC),
        )
        assert "linkedin.com" in profile_www.url

    def test_linkedin_profile_total_experience_years(self, sample_experience: Experience) -> None:
        """LinkedInProfile should calculate total years of experience."""
        experiences = [
            Experience(
                title="Senior Dev",
                company="Current",
                start_date=date(2020, 1, 1),
                end_date=date(2023, 1, 1),
            ),
            Experience(
                title="Junior Dev",
                company="Previous",
                start_date=date(2018, 1, 1),
                end_date=date(2020, 1, 1),
            ),
        ]
        profile = LinkedInProfile(
            id="exp123",
            url="https://linkedin.com/in/experienced",
            name="Experienced Dev",
            experience=experiences,
            last_fetched=datetime.now(UTC),
        )
        # 3 years + 2 years = 5 years
        assert profile.total_experience_months == 60

    def test_linkedin_profile_no_experience(self) -> None:
        """LinkedInProfile should handle no experience gracefully."""
        profile = LinkedInProfile(
            id="new123",
            url="https://linkedin.com/in/newgrad",
            name="New Grad",
            last_fetched=datetime.now(UTC),
        )
        assert profile.total_experience_months == 0

    def test_linkedin_profile_has_profile_picture(self) -> None:
        """LinkedInProfile should check if profile picture exists."""
        with_picture = LinkedInProfile(
            id="pic123",
            url="https://linkedin.com/in/withpic",
            name="Has Picture",
            profile_picture_url="https://linkedin.com/photo.jpg",
            last_fetched=datetime.now(UTC),
        )
        assert with_picture.has_profile_picture is True

        without_picture = LinkedInProfile(
            id="nopic123",
            url="https://linkedin.com/in/nopic",
            name="No Picture",
            last_fetched=datetime.now(UTC),
        )
        assert without_picture.has_profile_picture is False

    def test_linkedin_profile_is_new_account(self) -> None:
        """LinkedInProfile should identify new accounts based on experience dates."""
        # Profile with only recent experience (less than 6 months of history)
        recent_profile = LinkedInProfile(
            id="recent123",
            url="https://linkedin.com/in/recent",
            name="Recent User",
            experience=[
                Experience(
                    title="Developer",
                    company="New Job",
                    start_date=date.today().replace(month=max(1, date.today().month - 3)),
                    is_current=True,
                )
            ],
            last_fetched=datetime.now(UTC),
        )
        # New account detection based on earliest experience date
        assert recent_profile.earliest_experience_date is not None

    def test_linkedin_profile_earliest_experience_date(self) -> None:
        """LinkedInProfile should find the earliest experience start date."""
        experiences = [
            Experience(
                title="Current",
                company="Now",
                start_date=date(2022, 1, 1),
                is_current=True,
            ),
            Experience(
                title="Previous",
                company="Before",
                start_date=date(2018, 6, 1),
                end_date=date(2022, 1, 1),
            ),
            Experience(
                title="First",
                company="Start",
                start_date=date(2015, 9, 1),
                end_date=date(2018, 6, 1),
            ),
        ]
        profile = LinkedInProfile(
            id="hist123",
            url="https://linkedin.com/in/history",
            name="History",
            experience=experiences,
            last_fetched=datetime.now(UTC),
        )
        assert profile.earliest_experience_date == date(2015, 9, 1)

    def test_linkedin_profile_earliest_experience_date_none(self) -> None:
        """LinkedInProfile should return None when no experience dates exist."""
        profile = LinkedInProfile(
            id="nodates123",
            url="https://linkedin.com/in/nodates",
            name="No Dates",
            experience=[Experience(title="Dev", company="Unknown")],
            last_fetched=datetime.now(UTC),
        )
        assert profile.earliest_experience_date is None
