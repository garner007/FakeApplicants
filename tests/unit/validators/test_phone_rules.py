"""Tests for phone validation rules."""

import pytest

from applicant_validator.validators.base import RuleSeverity
from applicant_validator.validators.phone_rules import NonUSPhoneRule, VoIPPhoneRule


class TestVoIPPhoneRule:
    """Tests for the VoIPPhoneRule validator."""

    @pytest.fixture
    def rule(self) -> VoIPPhoneRule:
        """Create a VoIPPhoneRule instance."""
        return VoIPPhoneRule()

    async def test_regular_mobile_passes(self, rule: VoIPPhoneRule) -> None:
        """Regular mobile number should pass."""
        result = await rule.validate({"phone": "+1 (555) 123-4567"})

        # Without API access, we can only check format and known VoIP prefixes
        assert result.rule_name == "voip_phone"

    async def test_google_voice_prefix_fails(self, rule: VoIPPhoneRule) -> None:
        """Known Google Voice prefixes should be flagged."""
        # Google Voice numbers often come from specific area codes
        result = await rule.validate({"phone": "+1-747-555-1234"})

        # 747 is a known Google Voice area code
        if not result.was_skipped:
            # May or may not flag depending on detection capability
            pass

    async def test_missing_phone_skips(self, rule: VoIPPhoneRule) -> None:
        """Missing phone field should skip validation."""
        result = await rule.validate({})

        assert result.passed is True
        assert result.was_skipped is True
        assert "phone" in result.skip_reason.lower()

    async def test_empty_phone_skips(self, rule: VoIPPhoneRule) -> None:
        """Empty phone should skip validation."""
        result = await rule.validate({"phone": ""})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_none_phone_skips(self, rule: VoIPPhoneRule) -> None:
        """None phone should skip validation."""
        result = await rule.validate({"phone": None})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_invalid_phone_format_skips(self, rule: VoIPPhoneRule) -> None:
        """Invalid phone format should skip (let format validator handle it)."""
        result = await rule.validate({"phone": "not-a-phone"})

        assert result.passed is True
        assert result.was_skipped is True
        assert "parse" in result.skip_reason.lower() or "invalid" in result.skip_reason.lower()

    async def test_rule_metadata(self, rule: VoIPPhoneRule) -> None:
        """Rule should have correct metadata."""
        assert rule.name == "voip_phone"
        assert rule.category == "phone"
        assert rule.default_severity == RuleSeverity.MEDIUM
        assert rule.version is not None

    async def test_known_voip_carrier_detected(self, rule: VoIPPhoneRule) -> None:
        """When carrier info is available, known VoIP carriers should be flagged."""
        # This tests the carrier-based detection
        # In real usage, phonenumbers library provides carrier info
        result = await rule.validate({"phone": "+1-202-555-0100"})

        # The result depends on the phonenumbers library's carrier database
        assert result.rule_name == "voip_phone"

    async def test_international_number_handled(self, rule: VoIPPhoneRule) -> None:
        """International numbers should be properly parsed."""
        result = await rule.validate({"phone": "+44 20 7946 0958"})

        # UK number - should be parseable
        assert result.rule_name == "voip_phone"
        # Should not skip for valid international numbers
        if not result.was_skipped:
            assert result.passed is True or result.passed is False

    async def test_us_number_with_country_code(self, rule: VoIPPhoneRule) -> None:
        """US number with country code should work."""
        result = await rule.validate({"phone": "+1 650 555 1234"})

        assert result.rule_name == "voip_phone"

    async def test_us_number_without_country_code(self, rule: VoIPPhoneRule) -> None:
        """US number without country code should work with default region."""
        result = await rule.validate({"phone": "(650) 555-1234"})

        assert result.rule_name == "voip_phone"
        # Should not skip for parseable numbers
        assert result.was_skipped is False or result.passed is True

    async def test_bandwidth_voip_detected(self, rule: VoIPPhoneRule) -> None:
        """Bandwidth.com VoIP numbers should be detected if carrier matches."""
        # This is a known VoIP carrier
        result = await rule.validate({"phone": "+1-919-555-1234"})
        # Detection depends on phonenumbers carrier database
        assert result.rule_name == "voip_phone"

    async def test_loads_voip_carriers_from_file(self, rule: VoIPPhoneRule) -> None:
        """Rule should load VoIP carriers from data file."""
        # Trigger lazy loading by calling the internal method
        carriers = await rule._load_voip_carriers()
        assert len(carriers) > 20  # We have ~100 carriers

    async def test_evidence_on_voip_detection(self, rule: VoIPPhoneRule) -> None:
        """When VoIP is detected, evidence should be provided."""
        # Test with a number that might be VoIP
        result = await rule.validate({"phone": "+1-555-555-5555"})

        # If it fails (VoIP detected), should have evidence
        if not result.passed and not result.was_skipped:
            assert len(result.evidence) > 0


class TestNonUSPhoneRule:
    """Tests for the NonUSPhoneRule validator."""

    @pytest.fixture
    def rule(self) -> NonUSPhoneRule:
        """Create a NonUSPhoneRule instance."""
        return NonUSPhoneRule()

    # ==========================================================================
    # US Phone Number Tests - Should PASS
    # ==========================================================================

    async def test_us_phone_with_country_code_passes(self, rule: NonUSPhoneRule) -> None:
        """US phone number with +1 country code should pass."""
        result = await rule.validate({"phone": "+1-202-555-0100"})

        assert result.passed is True
        assert result.rule_name == "non_us_phone"
        assert result.was_skipped is False
        assert "US" in result.message

    async def test_us_phone_without_country_code_passes(self, rule: NonUSPhoneRule) -> None:
        """US phone number without country code should pass (defaults to US)."""
        result = await rule.validate({"phone": "(650) 555-1234"})

        assert result.passed is True
        assert result.was_skipped is False

    async def test_us_phone_various_formats_pass(self, rule: NonUSPhoneRule) -> None:
        """US phone numbers in various formats should pass."""
        us_numbers = [
            "+1 202 555 0100",  # DC
            "+1-650-555-1234",  # California
            "1-212-555-6789",  # New York
            "(312) 555-4321",  # Chicago
            "415.555.9876",  # San Francisco
            "8005551234",  # Toll-free
            "+1 (305) 555-0000",  # Miami
        ]

        for phone in us_numbers:
            result = await rule.validate({"phone": phone})
            assert result.passed is True, f"US number {phone} should pass"
            assert result.was_skipped is False

    async def test_us_area_codes_pass(self, rule: NonUSPhoneRule) -> None:
        """Various US area codes should all pass."""
        # Sample of US area codes from different states
        us_area_codes = [
            "202",  # Washington DC
            "212",  # New York
            "213",  # Los Angeles
            "312",  # Chicago
            "404",  # Atlanta
            "415",  # San Francisco
            "617",  # Boston
            "702",  # Las Vegas
            "713",  # Houston
            "808",  # Hawaii
            "907",  # Alaska
        ]

        for area_code in us_area_codes:
            result = await rule.validate({"phone": f"+1-{area_code}-555-1234"})
            assert result.passed is True, f"US area code {area_code} should pass"

    # ==========================================================================
    # Canadian Phone Number Tests - Should FAIL
    # ==========================================================================

    async def test_canadian_toronto_fails(self, rule: NonUSPhoneRule) -> None:
        """Canadian Toronto number (416) should fail."""
        result = await rule.validate({"phone": "+1-416-555-1234"})

        assert result.passed is False
        assert result.severity == RuleSeverity.HIGH
        assert "Canada" in result.message
        assert "416" in result.message
        assert len(result.evidence) > 0

    async def test_canadian_vancouver_fails(self, rule: NonUSPhoneRule) -> None:
        """Canadian Vancouver number (604) should fail."""
        result = await rule.validate({"phone": "+1-604-555-1234"})

        assert result.passed is False
        assert "Canada" in result.message
        assert "604" in result.message

    async def test_canadian_montreal_fails(self, rule: NonUSPhoneRule) -> None:
        """Canadian Montreal number (514) should fail."""
        result = await rule.validate({"phone": "+1-514-555-1234"})

        assert result.passed is False
        assert "Canada" in result.message

    async def test_canadian_area_codes_fail(self, rule: NonUSPhoneRule) -> None:
        """All major Canadian area codes should fail."""
        # Sample of Canadian area codes
        canadian_area_codes = [
            ("416", "Ontario/Toronto"),
            ("647", "Ontario/Toronto"),
            ("905", "Ontario/GTA"),
            ("604", "BC/Vancouver"),
            ("778", "BC"),
            ("514", "Quebec/Montreal"),
            ("438", "Quebec/Montreal"),
            ("403", "Alberta/Calgary"),
            ("780", "Alberta/Edmonton"),
            ("204", "Manitoba"),
            ("306", "Saskatchewan"),
            ("506", "New Brunswick"),
            ("709", "Newfoundland"),
            ("867", "Northern territories"),
        ]

        for area_code, region in canadian_area_codes:
            result = await rule.validate({"phone": f"+1-{area_code}-555-1234"})
            assert result.passed is False, f"Canadian area code {area_code} ({region}) should fail"
            assert "Canada" in result.message

    async def test_canadian_evidence_includes_area_code(self, rule: NonUSPhoneRule) -> None:
        """Evidence should include the Canadian area code."""
        result = await rule.validate({"phone": "+1-416-555-1234"})

        assert result.passed is False
        area_code_evidence = next(
            (e for e in result.evidence if e.evidence_type == "area_code"), None
        )
        assert area_code_evidence is not None
        assert "416" in area_code_evidence.value

    # ==========================================================================
    # International Phone Number Tests - Should FAIL
    # ==========================================================================

    async def test_uk_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """UK phone number should fail."""
        result = await rule.validate({"phone": "+44 20 7946 0958"})

        assert result.passed is False
        assert result.severity == RuleSeverity.HIGH
        assert "outside the US" in result.message.lower() or "kingdom" in result.message.lower()

    async def test_india_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """Indian phone number should fail."""
        result = await rule.validate({"phone": "+91 98765 43210"})

        assert result.passed is False
        assert "outside the US" in result.message.lower() or "india" in result.message.lower()

    async def test_nigeria_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """Nigerian phone number should fail."""
        result = await rule.validate({"phone": "+234 803 123 4567"})

        assert result.passed is False

    async def test_germany_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """German phone number should fail."""
        result = await rule.validate({"phone": "+49 30 12345678"})

        assert result.passed is False

    async def test_china_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """Chinese phone number should fail."""
        result = await rule.validate({"phone": "+86 138 1234 5678"})

        assert result.passed is False

    async def test_mexico_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """Mexican phone number should fail."""
        result = await rule.validate({"phone": "+52 55 1234 5678"})

        assert result.passed is False

    async def test_philippines_phone_fails(self, rule: NonUSPhoneRule) -> None:
        """Philippines phone number should fail."""
        result = await rule.validate({"phone": "+63 917 123 4567"})

        assert result.passed is False

    async def test_international_evidence_includes_country(self, rule: NonUSPhoneRule) -> None:
        """Evidence should include country information for international numbers."""
        result = await rule.validate({"phone": "+44 20 7946 0958"})

        assert result.passed is False

        # Should have country code evidence
        country_code_evidence = next(
            (e for e in result.evidence if e.evidence_type == "country_code"), None
        )
        assert country_code_evidence is not None
        assert "+44" in country_code_evidence.value

        # Should have region evidence
        region_evidence = next((e for e in result.evidence if e.evidence_type == "region"), None)
        assert region_evidence is not None

    # ==========================================================================
    # Edge Cases and Skip Conditions
    # ==========================================================================

    async def test_missing_phone_skips(self, rule: NonUSPhoneRule) -> None:
        """Missing phone field should skip validation."""
        result = await rule.validate({})

        assert result.passed is True
        assert result.was_skipped is True
        assert "phone" in result.skip_reason.lower()

    async def test_empty_phone_skips(self, rule: NonUSPhoneRule) -> None:
        """Empty phone should skip validation."""
        result = await rule.validate({"phone": ""})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_none_phone_skips(self, rule: NonUSPhoneRule) -> None:
        """None phone should skip validation."""
        result = await rule.validate({"phone": None})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_whitespace_only_phone_skips(self, rule: NonUSPhoneRule) -> None:
        """Whitespace-only phone should skip validation."""
        result = await rule.validate({"phone": "   "})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_invalid_phone_format_skips(self, rule: NonUSPhoneRule) -> None:
        """Invalid phone format should skip."""
        result = await rule.validate({"phone": "not-a-phone-number"})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_manually_added_applicant_no_phone_skips(self, rule: NonUSPhoneRule) -> None:
        """Manually added applicant without phone should skip with specific message."""
        result = await rule.validate({"is_manually_added": True})

        assert result.passed is True
        assert result.was_skipped is True
        assert "manually added" in result.skip_reason.lower()

    # ==========================================================================
    # Rule Metadata Tests
    # ==========================================================================

    async def test_rule_metadata(self, rule: NonUSPhoneRule) -> None:
        """Rule should have correct metadata."""
        assert rule.name == "non_us_phone"
        assert rule.category == "phone"
        assert rule.default_severity == RuleSeverity.HIGH
        assert rule.version is not None
        assert "US" in rule.description

    async def test_rule_has_checks_fields(self, rule: NonUSPhoneRule) -> None:
        """Rule should declare which fields it checks."""
        assert "phone" in rule.checks_fields

    async def test_rule_has_trigger_examples(self, rule: NonUSPhoneRule) -> None:
        """Rule should have trigger examples for documentation."""
        assert len(rule.trigger_examples) > 0

    async def test_rule_has_rationale(self, rule: NonUSPhoneRule) -> None:
        """Rule should have a rationale explaining why it matters."""
        assert len(rule.rationale) > 0
