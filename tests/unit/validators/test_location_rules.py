"""Tests for location validation rules."""

import pytest

from applicant_validator.validators.base import RuleSeverity
from applicant_validator.validators.location_rules import NonUSLocationRule


class TestNonUSLocationRule:
    """Tests for the NonUSLocationRule validator."""

    @pytest.fixture
    def rule(self) -> NonUSLocationRule:
        """Create a NonUSLocationRule instance."""
        return NonUSLocationRule()

    # ==========================================================================
    # US Location Tests - Should PASS
    # ==========================================================================

    async def test_us_city_state_passes(self, rule: NonUSLocationRule) -> None:
        """US city with state abbreviation should pass."""
        result = await rule.validate({"location": "Boston, MA"})

        assert result.passed is True
        assert result.rule_name == "non_us_location"
        assert result.was_skipped is False

    async def test_us_city_state_full_name_passes(self, rule: NonUSLocationRule) -> None:
        """US city with full state name should pass."""
        result = await rule.validate({"location": "San Francisco, California"})

        assert result.passed is True

    async def test_us_city_state_zip_passes(self, rule: NonUSLocationRule) -> None:
        """US city with state and ZIP code should pass."""
        result = await rule.validate({"location": "New York, NY 10001"})

        assert result.passed is True

    async def test_us_city_state_zip_plus4_passes(self, rule: NonUSLocationRule) -> None:
        """US city with state and ZIP+4 should pass."""
        result = await rule.validate({"location": "Chicago, IL 60601-1234"})

        assert result.passed is True

    async def test_us_with_usa_indicator_passes(self, rule: NonUSLocationRule) -> None:
        """Location with USA indicator should pass."""
        result = await rule.validate({"location": "Austin, TX, USA"})

        assert result.passed is True

    async def test_us_with_united_states_passes(self, rule: NonUSLocationRule) -> None:
        """Location with 'United States' should pass."""
        result = await rule.validate({"location": "Seattle, WA, United States"})

        assert result.passed is True

    async def test_us_various_states_pass(self, rule: NonUSLocationRule) -> None:
        """Various US state locations should all pass."""
        us_locations = [
            "New York, NY",
            "Los Angeles, CA",
            "Chicago, IL",
            "Houston, TX",
            "Phoenix, AZ",
            "Philadelphia, PA",
            "San Antonio, TX",
            "San Diego, CA",
            "Dallas, TX",
            "San Jose, CA",
            "Austin, TX",
            "Jacksonville, FL",
            "Fort Worth, TX",
            "Columbus, OH",
            "Charlotte, NC",
            "Indianapolis, IN",
            "Seattle, WA",
            "Denver, CO",
            "Boston, MA",
            "Nashville, TN",
            "Portland, OR",
            "Las Vegas, NV",
            "Detroit, MI",
            "Memphis, TN",
            "Honolulu, HI",
            "Anchorage, AK",
        ]

        for location in us_locations:
            result = await rule.validate({"location": location})
            assert result.passed is True, f"US location '{location}' should pass"

    async def test_us_state_full_names_pass(self, rule: NonUSLocationRule) -> None:
        """Full US state names should pass."""
        states = [
            "New York",
            "California",
            "Texas",
            "Florida",
            "Illinois",
            "Pennsylvania",
            "Ohio",
            "Georgia",
            "North Carolina",
            "Michigan",
            "New Jersey",
            "Virginia",
            "Washington",
            "Massachusetts",
            "Arizona",
            "Colorado",
            "Tennessee",
            "Maryland",
            "Minnesota",
            "Wisconsin",
        ]

        for state in states:
            result = await rule.validate({"location": f"Some City, {state}"})
            assert result.passed is True, f"State '{state}' should pass"

    async def test_us_territories_pass(self, rule: NonUSLocationRule) -> None:
        """US territories should pass."""
        territories = [
            ("Washington, DC", "DC"),
            ("San Juan, PR", "Puerto Rico"),
            ("Charlotte Amalie, VI", "Virgin Islands"),
            ("Hagatna, GU", "Guam"),
        ]

        for location, description in territories:
            result = await rule.validate({"location": location})
            assert result.passed is True, f"US territory '{description}' should pass"

    async def test_simple_city_name_passes(self, rule: NonUSLocationRule) -> None:
        """Simple city name without state should pass (insufficient data)."""
        result = await rule.validate({"location": "Springfield"})

        assert result.passed is True
        assert "insufficient" in result.message.lower()

    # ==========================================================================
    # Canadian Location Tests - Should FAIL
    # ==========================================================================

    async def test_canadian_toronto_fails(self, rule: NonUSLocationRule) -> None:
        """Toronto, ON should fail."""
        result = await rule.validate({"location": "Toronto, ON"})

        assert result.passed is False
        assert result.severity == RuleSeverity.HIGH
        assert "Canada" in result.message

    async def test_canadian_vancouver_fails(self, rule: NonUSLocationRule) -> None:
        """Vancouver, BC should fail."""
        result = await rule.validate({"location": "Vancouver, BC"})

        assert result.passed is False
        assert "Canada" in result.message

    async def test_canadian_montreal_fails(self, rule: NonUSLocationRule) -> None:
        """Montreal, QC should fail."""
        result = await rule.validate({"location": "Montreal, QC"})

        assert result.passed is False
        assert "Canada" in result.message

    async def test_canadian_province_abbreviations_fail(self, rule: NonUSLocationRule) -> None:
        """All Canadian province abbreviations should fail."""
        canadian_locations = [
            ("Calgary, AB", "Alberta"),
            ("Victoria, BC", "British Columbia"),
            ("Winnipeg, MB", "Manitoba"),
            ("Fredericton, NB", "New Brunswick"),
            ("St. John's, NL", "Newfoundland"),
            ("Yellowknife, NT", "Northwest Territories"),
            ("Halifax, NS", "Nova Scotia"),
            ("Iqaluit, NU", "Nunavut"),
            ("Ottawa, ON", "Ontario"),
            ("Charlottetown, PE", "Prince Edward Island"),
            ("Quebec City, QC", "Quebec"),
            ("Regina, SK", "Saskatchewan"),
            ("Whitehorse, YT", "Yukon"),
        ]

        for location, province in canadian_locations:
            result = await rule.validate({"location": location})
            assert (
                result.passed is False
            ), f"Canadian location '{location}' ({province}) should fail"
            assert "Canada" in result.message

    async def test_canadian_province_full_names_fail(self, rule: NonUSLocationRule) -> None:
        """Canadian province full names should fail."""
        provinces = [
            "Alberta",
            "British Columbia",
            "Manitoba",
            "Ontario",
            "Quebec",
            "Saskatchewan",
            "Nova Scotia",
        ]

        for province in provinces:
            result = await rule.validate({"location": f"Some City, {province}"})
            assert result.passed is False, f"Province '{province}' should fail"
            assert "Canada" in result.message

    async def test_canadian_with_canada_fails(self, rule: NonUSLocationRule) -> None:
        """Location with 'Canada' should fail."""
        result = await rule.validate({"location": "Toronto, Canada"})

        assert result.passed is False
        assert "Canada" in result.message

    async def test_canadian_cities_fail(self, rule: NonUSLocationRule) -> None:
        """Major Canadian cities should be detected and fail."""
        canadian_cities = [
            "Toronto",
            "Vancouver",
            "Montreal",
            "Calgary",
            "Ottawa",
            "Edmonton",
        ]

        for city in canadian_cities:
            result = await rule.validate({"location": city})
            assert result.passed is False, f"Canadian city '{city}' should fail"

    async def test_canadian_evidence_includes_province(self, rule: NonUSLocationRule) -> None:
        """Evidence should include the Canadian province."""
        result = await rule.validate({"location": "Toronto, ON"})

        assert result.passed is False
        province_evidence = next(
            (e for e in result.evidence if e.evidence_type == "canadian_province"), None
        )
        assert province_evidence is not None
        assert "ON" in province_evidence.value

    # ==========================================================================
    # International Location Tests - Should FAIL
    # ==========================================================================

    async def test_uk_london_fails(self, rule: NonUSLocationRule) -> None:
        """London, UK should fail."""
        result = await rule.validate({"location": "London, UK"})

        assert result.passed is False

    async def test_india_cities_fail(self, rule: NonUSLocationRule) -> None:
        """Indian cities should fail."""
        indian_cities = [
            "Mumbai, India",
            "Delhi",
            "Bangalore",
            "Hyderabad",
            "Chennai",
            "Kolkata",
        ]

        for city in indian_cities:
            result = await rule.validate({"location": city})
            assert result.passed is False, f"Indian location '{city}' should fail"

    async def test_nigeria_lagos_fails(self, rule: NonUSLocationRule) -> None:
        """Lagos, Nigeria should fail."""
        result = await rule.validate({"location": "Lagos, Nigeria"})

        assert result.passed is False

    async def test_philippines_cities_fail(self, rule: NonUSLocationRule) -> None:
        """Philippines cities should fail."""
        result = await rule.validate({"location": "Manila, Philippines"})

        assert result.passed is False

    async def test_pakistan_cities_fail(self, rule: NonUSLocationRule) -> None:
        """Pakistan cities should fail."""
        cities = ["Karachi", "Lahore", "Islamabad"]

        for city in cities:
            result = await rule.validate({"location": city})
            assert result.passed is False, f"Pakistan city '{city}' should fail"

    async def test_china_cities_fail(self, rule: NonUSLocationRule) -> None:
        """Chinese cities should fail."""
        cities = ["Beijing", "Shanghai"]

        for city in cities:
            result = await rule.validate({"location": city})
            assert result.passed is False, f"Chinese city '{city}' should fail"

    async def test_brazil_cities_fail(self, rule: NonUSLocationRule) -> None:
        """Brazilian cities should fail."""
        cities = ["São Paulo", "Rio de Janeiro"]

        for city in cities:
            result = await rule.validate({"location": city})
            assert result.passed is False, f"Brazilian city '{city}' should fail"

    async def test_african_countries_fail(self, rule: NonUSLocationRule) -> None:
        """African country locations should fail."""
        locations = [
            "Accra, Ghana",
            "Nairobi, Kenya",
            "Johannesburg, South Africa",
        ]

        for location in locations:
            result = await rule.validate({"location": location})
            assert result.passed is False, f"African location '{location}' should fail"

    async def test_european_countries_fail(self, rule: NonUSLocationRule) -> None:
        """European locations should fail."""
        locations = [
            "Berlin, Germany",
            "Paris, France",
            "Madrid, Spain",
            "Rome, Italy",
            "Amsterdam, Netherlands",
            "Warsaw, Poland",
        ]

        for location in locations:
            result = await rule.validate({"location": location})
            assert result.passed is False, f"European location '{location}' should fail"

    async def test_country_name_fails(self, rule: NonUSLocationRule) -> None:
        """Country names should fail."""
        countries = [
            "India",
            "Nigeria",
            "Pakistan",
            "Philippines",
            "United Kingdom",
            "UK",
            "China",
            "Russia",
            "Brazil",
            "Mexico",
            "Ghana",
            "Kenya",
            "South Africa",
            "Australia",
            "Germany",
            "France",
        ]

        for country in countries:
            result = await rule.validate({"location": country})
            assert result.passed is False, f"Country '{country}' should fail"

    async def test_international_evidence_includes_indicator(self, rule: NonUSLocationRule) -> None:
        """Evidence should include the international indicator found."""
        result = await rule.validate({"location": "Lagos, Nigeria"})

        assert result.passed is False
        indicator_evidence = next(
            (e for e in result.evidence if e.evidence_type == "international_indicator"), None
        )
        assert indicator_evidence is not None

    # ==========================================================================
    # Unrecognized Location Tests
    # ==========================================================================

    async def test_unknown_city_country_format_fails(self, rule: NonUSLocationRule) -> None:
        """Unknown location in 'City, Country' format should fail with low severity."""
        result = await rule.validate({"location": "Unknown City, Unknown Country"})

        assert result.passed is False
        # Should be low severity for uncertain cases
        assert result.severity == RuleSeverity.LOW

    # ==========================================================================
    # Edge Cases and Skip Conditions
    # ==========================================================================

    async def test_missing_location_skips(self, rule: NonUSLocationRule) -> None:
        """Missing location field should skip validation."""
        result = await rule.validate({})

        assert result.passed is True
        assert result.was_skipped is True
        assert "location" in result.skip_reason.lower()

    async def test_empty_location_skips(self, rule: NonUSLocationRule) -> None:
        """Empty location should skip validation."""
        result = await rule.validate({"location": ""})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_none_location_skips(self, rule: NonUSLocationRule) -> None:
        """None location should skip validation."""
        result = await rule.validate({"location": None})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_whitespace_only_location_skips(self, rule: NonUSLocationRule) -> None:
        """Whitespace-only location should skip validation."""
        result = await rule.validate({"location": "   "})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_manually_added_applicant_no_location_skips(
        self, rule: NonUSLocationRule
    ) -> None:
        """Manually added applicant without location should skip with specific message."""
        result = await rule.validate({"is_manually_added": True})

        assert result.passed is True
        assert result.was_skipped is True
        assert "manually added" in result.skip_reason.lower()

    # ==========================================================================
    # Case Sensitivity Tests
    # ==========================================================================

    async def test_case_insensitive_state_matching(self, rule: NonUSLocationRule) -> None:
        """State matching should be case-insensitive."""
        variations = [
            "Boston, MA",
            "Boston, ma",
            "BOSTON, MA",
            "boston, Ma",
        ]

        for location in variations:
            result = await rule.validate({"location": location})
            assert result.passed is True, f"Location '{location}' should pass"

    async def test_case_insensitive_international_matching(self, rule: NonUSLocationRule) -> None:
        """International indicator matching should be case-insensitive."""
        variations = [
            "LONDON, UK",
            "london, uk",
            "London, Uk",
            "LAGOS, NIGERIA",
            "lagos, nigeria",
        ]

        for location in variations:
            result = await rule.validate({"location": location})
            assert result.passed is False, f"Location '{location}' should fail"

    async def test_case_insensitive_canadian_matching(self, rule: NonUSLocationRule) -> None:
        """Canadian province matching should be case-insensitive."""
        variations = [
            "Toronto, ON",
            "toronto, on",
            "TORONTO, ON",
            "Vancouver, bc",
        ]

        for location in variations:
            result = await rule.validate({"location": location})
            assert result.passed is False, f"Canadian location '{location}' should fail"

    # ==========================================================================
    # Rule Metadata Tests
    # ==========================================================================

    async def test_rule_metadata(self, rule: NonUSLocationRule) -> None:
        """Rule should have correct metadata."""
        assert rule.name == "non_us_location"
        assert rule.category == "location"
        assert rule.default_severity == RuleSeverity.HIGH
        assert rule.version is not None
        assert "US" in rule.description

    async def test_rule_has_checks_fields(self, rule: NonUSLocationRule) -> None:
        """Rule should declare which fields it checks."""
        assert "location" in rule.checks_fields

    async def test_rule_has_trigger_examples(self, rule: NonUSLocationRule) -> None:
        """Rule should have trigger examples for documentation."""
        assert len(rule.trigger_examples) > 0
        # Should include Canadian and international examples
        examples_str = " ".join(rule.trigger_examples)
        assert "Canada" in examples_str or "ON" in examples_str or "Toronto" in examples_str

    async def test_rule_has_rationale(self, rule: NonUSLocationRule) -> None:
        """Rule should have a rationale explaining why it matters."""
        assert len(rule.rationale) > 0
        assert "US" in rule.rationale or "Canada" in rule.rationale

    # ==========================================================================
    # Evidence Tests
    # ==========================================================================

    async def test_evidence_includes_input_value(self, rule: NonUSLocationRule) -> None:
        """Evidence should include the input location value."""
        result = await rule.validate({"location": "Toronto, ON"})

        input_evidence = next(
            (e for e in result.evidence if e.evidence_type == "input_value"), None
        )
        assert input_evidence is not None
        assert input_evidence.value == "Toronto, ON"

    async def test_evidence_on_us_pass_empty(self, rule: NonUSLocationRule) -> None:
        """Passing results should not have extensive evidence."""
        result = await rule.validate({"location": "Boston, MA"})

        assert result.passed is True
        # Passing results may have minimal or no evidence
        assert len(result.evidence) <= 1
